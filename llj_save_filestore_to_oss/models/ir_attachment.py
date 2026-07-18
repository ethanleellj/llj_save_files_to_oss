import os
import logging
import imghdr
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import str2bool

_logger = logging.getLogger(__name__)

import re

_UNSAFE_RE = re.compile(r"[^\w.\-]+")

# MIME type to file extension mapping
_MIME_TO_EXT = {
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "png": ".png",
    "gif": ".gif",
    "bmp": ".bmp",
    "webp": ".webp",
    "tiff": ".tiff",
}


def _detect_image_extension(bin_data):
    """Detect image format from binary data and return the appropriate extension."""
    if not bin_data or len(bin_data) < 32:
        return ""
    fmt = imghdr.what(None, h=bin_data)
    if fmt:
        return _MIME_TO_EXT.get(fmt, ".%s" % fmt)
    return ""


def _sanitize_filename(name, bin_data=None):
    """Return a filesystem-safe version of an attachment name with auto-detected extension."""
    base = os.path.basename(name or "attachment")
    base = _UNSAFE_RE.sub("_", base).strip("._")
    if not base:
        base = "attachment"

    # Auto-detect and append image extension if not already present
    if bin_data and "." not in base:
        ext = _detect_image_extension(bin_data)
        if ext:
            base = base + ext

    return base

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    llj_oss_key = fields.Char(
        string="OSS Key",
        compute="_compute_llj_oss_refs",
        help="Full key of the object in the OSS bucket: [database]/[store_fname].",
    )
    llj_oss_url = fields.Char(
        string="OSS URL",
        compute="_compute_llj_oss_refs",
        help="Direct URL to the object on OSS (CDN domain if configured).",
    )

    @api.depends("store_fname")
    def _compute_llj_oss_refs(self):
        enabled = self._llj_oss_enabled()
        for attach in self:
            if enabled and attach.store_fname and attach._llj_is_product_attachment():
                key = attach._llj_oss_key(attach.store_fname)
                attach.llj_oss_key = key
                attach.llj_oss_url = attach._llj_oss_public_url(key)
            else:
                attach.llj_oss_key = False
                attach.llj_oss_url = False

    @api.model
    def _llj_oss_enabled(self):
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("llj_oss.enabled", "False")
        )

    @api.model
    def _llj_get_bucket(self):
        try:
            import oss2
        except ImportError:
            raise UserError(
                _(
                    "The python package oss2 is required to use Alibaba Cloud "
                    "OSS. Install it with: pip install oss2"
                )
            )
        ICP = self.env["ir.config_parameter"].sudo()
        access_id = ICP.get_param("llj_oss.access_key_id")
        access_secret = ICP.get_param("llj_oss.access_key_secret")
        endpoint = ICP.get_param("llj_oss.endpoint")
        bucket_name = ICP.get_param("llj_oss.bucket_name")
        if not all([access_id, access_secret, endpoint, bucket_name]):
            raise UserError(
                _(
                    "Alibaba Cloud OSS is not fully configured. Set the access "
                    "key, secret, endpoint and bucket in Settings."
                )
            )
        auth = oss2.Auth(access_id, access_secret)
        return oss2.Bucket(auth, endpoint, bucket_name)

    @api.model
    def _llj_oss_key(self, fname):
        return "%s/%s" % (self.env.cr.dbname, fname)

    @api.model
    def _llj_oss_public_url(self, key):
        ICP = self.env["ir.config_parameter"].sudo()
        cdn = ICP.get_param("llj_oss.cdn_domain")
        bucket_name = ICP.get_param("llj_oss.bucket_name")
        endpoint = (ICP.get_param("llj_oss.endpoint") or "").rstrip("/")
        if cdn:
            return "%s/%s" % (cdn.rstrip("/"), key)
        if endpoint and bucket_name:
            return "%s/%s/%s" % (endpoint, bucket_name, key)
        return False

    @api.model
    def _llj_is_product_attachment(self):
        if self.store_fname and self.store_fname.startswith("products/"):
            return True
        if self.env.context.get("llj_id_code") and self.env.context.get("llj_attachment_name"):
            return True
        return False

    @api.model
    def _llj_compute_fname(self, bin_value, checksum):
        id_code = self.env.context.get("llj_id_code")
        name = self.env.context.get("llj_attachment_name")
        if id_code and name:
            return "products/%s/%s" % (id_code, _sanitize_filename(name, bin_value))
        return checksum[:2] + "/" + checksum

    @api.model
    def _file_write(self, bin_value, checksum):
        if not self._llj_oss_enabled():
            return super()._file_write(bin_value, checksum)
        if not self._llj_is_product_attachment():
            return super()._file_write(bin_value, checksum)
        fname = self._llj_compute_fname(bin_value, checksum)
        bucket = self._llj_get_bucket()
        bucket.put_object(self._llj_oss_key(fname), bin_value)
        return fname

    @api.model
    def _file_read(self, fname, size=None):
        if not self._llj_oss_enabled() or not fname:
            return super()._file_read(fname, size)
        if not fname.startswith("products/"):
            return super()._file_read(fname, size)
        bucket = self._llj_get_bucket()
        try:
            result = bucket.get_object(self._llj_oss_key(fname))
            data = result.read()
        except Exception:
            _logger.exception("OSS _file_read failed for %s", fname)
            return b""
        if size is not None:
            return data[:size]
        return data

    @api.model
    def _file_delete(self, fname):
        if not self._llj_oss_enabled() or not fname:
            return super()._file_delete(fname)
        if not fname.startswith("products/"):
            return super()._file_delete(fname)
        still_used = self.sudo().search_count(
            [("store_fname", "=", fname)], limit=1
        )
        if still_used:
            return
        try:
            bucket = self._llj_get_bucket()
            bucket.delete_object(self._llj_oss_key(fname))
        except Exception:
            _logger.exception("OSS _file_delete failed for %s", fname)

    def _llj_download_from_oss_to_local(self):
        if not self._llj_oss_enabled() or not self.store_fname:
            return
        if not self.store_fname.startswith("products/"):
            return
        filestore_path = self.env["ir.attachment"]._filestore()
        local_path = os.path.join(filestore_path, self.store_fname)
        if os.path.exists(local_path):
            return
        bucket = self._llj_get_bucket()
        try:
            result = bucket.get_object(self._llj_oss_key(self.store_fname))
            data = result.read()
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            _logger.info("Downloaded from OSS to local: %s", self.store_fname)
        except Exception:
            _logger.exception("OSS download failed for %s", self.store_fname)

    def _to_http_stream(self):
        if self._llj_oss_enabled() and self.store_fname and self.store_fname.startswith("products/"):
            self._llj_download_from_oss_to_local()
        return super()._to_http_stream()
