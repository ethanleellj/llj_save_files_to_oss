import os
import re
import logging
import imghdr
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import str2bool

_logger = logging.getLogger(__name__)

# models whose attachments must follow the /products/[llj_id_code]/ layout
_PRODUCT_MODELS = ("product.template", "product.product")

# strip everything that is not safe for a filename on a posix filesystem
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
    """Detect image format from binary data and return the appropriate extension.

    Uses Python's imghdr module to detect the image format from the file header.
    Returns the extension with leading dot (e.g. '.jpg', '.png'), or empty string
    if the format cannot be determined.
    """
    if not bin_data or len(bin_data) < 32:
        return ""
    # imghdr returns format strings like 'jpeg', 'png', 'gif', etc.
    fmt = imghdr.what(None, h=bin_data)
    if fmt:
        return _MIME_TO_EXT.get(fmt, ".%s" % fmt)
    return ""


def _sanitize_filename(name, bin_data=None):
    """Return a filesystem-safe version of an attachment name.

    The user requirement is to keep the ``name`` field value (e.g.
    ``image_1920``) as the physical file name. We only neutralize path
    separators and other characters that would break the layout.

    If bin_data is provided and looks like an image, automatically append
    the appropriate file extension based on the detected MIME type.
    """
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _llj_get_id_code(self, res_model, res_id):
        """Return the llj_id_code of the product linked to an attachment.

        For product.product variants the code is read on the related
        product.template, so every variant of a template shares the same
        storage folder.
        """
        if not res_model or not res_id or res_model not in _PRODUCT_MODELS:
            return False
        if res_model == "product.template":
            product = self.env["product.template"].browse(res_id).exists()
            return product.llj_id_code if product else False
        # product.product
        variant = self.env["product.product"].browse(res_id).exists()
        if not variant:
            return False
        return variant.product_tmpl_id.llj_id_code

    @api.model
    def _llj_relative_path(self, id_code, name, bin_data=None):
        """Return the store_fname (relative to filestore) for a product file.

        Automatically appends the image extension based on binary content detection.
        """
        return "products/%s/%s" % (id_code, _sanitize_filename(name, bin_data))

    @api.model
    def _llj_oss_backend_active(self):
        """True when the llj_save_filestore_to_oss backend has been enabled.

        Read from ir.config_parameter so the two modules stay decoupled: when
        the OSS backend is active it owns the physical write, and this module
        only contributes the ``products/[llj_id_code]/`` path convention
        through the context flags that the OSS backend reads.
        """
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("llj_oss.enabled", "False")
        )

    # ------------------------------------------------------------------
    # Path override
    #
    # In Odoo 19 the storage path is decided by ``_get_path`` which is called
    # *both* to set ``store_fname`` (in _get_datas_related_values) and to write
    # the physical file (in _file_write). Overriding it is therefore enough to
    # relocate product attachments under ``products/[llj_id_code]/[name]``.
    # ------------------------------------------------------------------
    @api.model
    def _get_path(self, bin_data, sha):
        id_code = self.env.context.get("llj_id_code")
        name = self.env.context.get("llj_attachment_name")
        if (
            id_code
            and name
            and self._storage() == "file"
        ):
            fname = self._llj_relative_path(id_code, name, bin_data)
            full_path = self._full_path(fname)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # NOTE: no sha-collision check here. Product attachments are keyed
            # by name and are meant to be overwritten in place (e.g. updating
            # image_1920 replaces the previous file).
            return fname, full_path
        return super()._get_path(bin_data, sha)

    # ------------------------------------------------------------------
    # Write override
    #
    # The default ``_file_write`` skips writing when the file already exists
    # (sha-based deduplication: same checksum => same content). For product
    # files keyed by name we must overwrite in place, so we force the write.
    # When the OSS backend is active we let it own the physical storage.
    # ------------------------------------------------------------------
    @api.model
    def _file_write(self, bin_value, checksum):
        id_code = self.env.context.get("llj_id_code")
        name = self.env.context.get("llj_attachment_name")
        if (
            id_code
            and name
            and self._storage() == "file"
            and not self._llj_oss_backend_active()
        ):
            fname, full_path = self._get_path(bin_value, checksum)
            with open(full_path, "wb") as fp:
                fp.write(bin_value)
            return fname
        return super()._file_write(bin_value, checksum)

    # _file_read / _file_delete keep working untouched: they resolve
    # ``store_fname`` through ``_full_path`` which now contains
    # ``products/[id_code]/[name]``.

    # ------------------------------------------------------------------
    # Validation + context propagation on create
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Split the list so product attachments can be created one by one,
        # each with its own id_code/name propagated through the context down
        # to _get_path / _file_write.
        normal_vals, product_vals = [], []
        for vals in vals_list:
            if (
                vals.get("res_model") in _PRODUCT_MODELS
                and vals.get("res_id")
                and not self.env.context.get("llj_skip_path_check")
            ):
                product_vals.append(vals)
            else:
                normal_vals.append(vals)

        attachments = self.env["ir.attachment"]
        if normal_vals:
            attachments |= super().create(normal_vals)

        for vals in product_vals:
            id_code = self._llj_get_id_code(vals["res_model"], vals["res_id"])
            if not id_code:
                raise UserError(
                    _(
                        "You cannot upload an attachment to a product that has no "
                        "ID Code. Set the ID Code on the product first, then save "
                        "the product before uploading any attachment."
                    )
                )
            name = vals.get("name") or vals.get("datas_fname") or "attachment"
            rec = super(
                IrAttachment,
                self.with_context(llj_id_code=id_code, llj_attachment_name=name),
            ).create([vals])
            attachments |= rec
        return attachments

    # ------------------------------------------------------------------
    # Validation + context propagation on write (datas updated)
    # ------------------------------------------------------------------
    def write(self, vals):
        if (
            ("datas" in vals or "raw" in vals)
            and not self.env.context.get("llj_skip_path_check")
        ):
            # Only intercept when actual binary content is being pushed.
            has_content = bool(vals.get("datas") or vals.get("raw"))
            if has_content:
                product_atts = self.filtered(
                    lambda a: a.res_model in _PRODUCT_MODELS and a.res_id
                )
                other_atts = self - product_atts
                for att in product_atts:
                    id_code = self._llj_get_id_code(att.res_model, att.res_id)
                    if not id_code:
                        raise UserError(
                            _(
                                "You cannot upload an attachment to a product that "
                                "has no ID Code. Set the ID Code on the product first, "
                                "then save the product before uploading any attachment."
                            )
                        )
                    name = vals.get("name") or att.name or "attachment"
                    super(
                        IrAttachment,
                        att.with_context(
                            llj_id_code=id_code, llj_attachment_name=name
                        ),
                    ).write(vals)
                if other_atts:
                    super(IrAttachment, other_atts).write(vals)
                return True
        return super().write(vals)
