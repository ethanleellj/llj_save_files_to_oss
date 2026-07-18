import os
import base64
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    llj_id_code = fields.Char(
        string="ID Code",
        help="Unique identifier used to build the attachment storage folder "
        "(/products/[llj_id_code]/). Required before uploading any product "
        "image or attachment.",
        index=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Original high-resolution image (no compression)
    # ------------------------------------------------------------------
    llj_image_original = fields.Binary(
        string="Original Image",
        attachment=True,
        help="Original high-resolution product image stored without compression. "
        "Use this field to preserve the full quality of the uploaded image. "
        "The file is stored in OSS with its original extension preserved.",
    )
    llj_image_original_name = fields.Char(
        string="Original Image Filename",
        help="Original filename of the uploaded image, used to preserve the extension.",
    )
    llj_image_original_url = fields.Char(
        string="Original Image URL",
        compute="_compute_llj_image_original_url",
        help="Direct OSS URL to access the original high-resolution image.",
    )

    @api.depends("llj_image_original", "llj_id_code")
    def _compute_llj_image_original_url(self):
        """Compute the OSS URL for the original image.

        The URL is only available when:
        1. OSS backend is enabled (llj_oss.enabled = True)
        2. The product has an llj_id_code
        3. An original image has been uploaded
        """
        enabled = self.env["ir.attachment"]._llj_oss_backend_active()
        for product in self:
            if (
                enabled
                and product.llj_id_code
                and product.llj_image_original
                and product.llj_image_original_name
            ):
                # Build the OSS key path
                from .ir_attachment import _sanitize_filename
                name = _sanitize_filename(product.llj_image_original_name)
                key = "odoo/products/%s/%s" % (product.llj_id_code, name)
                # Get the public URL
                product.llj_image_original_url = self.env["ir.attachment"]._llj_oss_public_url(key)
            else:
                product.llj_image_original_url = False

    # A plain UNIQUE constraint treats empty strings ('') as equal values,
    # which would block several products from coexisting without a code.
    # NULLs are allowed to repeat in PostgreSQL, so empty values are stored
    # as NULL (see create/write overrides below).
    _sql_constraints = [
        (
            "llj_id_code_unique",
            "unique(llj_id_code)",
            "The ID Code must be unique across all products!",
        ),
    ]

    # ------------------------------------------------------------------
    # CRUD helpers: empty string -> NULL so the unique constraint does not
    # reject multiple products that simply have no ID Code yet.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "llj_id_code" in vals and not vals["llj_id_code"]:
                vals["llj_id_code"] = None
        return super().create(vals_list)

    def write(self, vals):
        # Normalize empty llj_id_code to None
        if "llj_id_code" in vals and not vals["llj_id_code"]:
            vals["llj_id_code"] = None

        # ----- Check ID Code before allowing image field updates -----
        # Product images (image_1920, image_1024, etc.) are stored directly on
        # product.template as binary fields, not as separate ir.attachment.
        # When the user edits any image, we must check that llj_id_code is set
        # before allowing the save - just like we do for explicit attachments.
        IMAGE_FIELDS = ("image_1920", "image_1024", "image_512", "image_256", "image_128")
        has_image_update = any(field in vals for field in IMAGE_FIELDS)
        if has_image_update:
            for product in self:
                # Already has an ID Code in the database -> OK
                if product.llj_id_code:
                    continue
                # No ID Code in DB, but the user is setting it in the same
                # form edit -> OK
                new_code = vals.get("llj_id_code")
                if new_code:
                    continue
                # No ID Code at all -> block
                raise UserError(
                    _(
                        "You cannot edit product images on a product that has no "
                        "ID Code. Set the ID Code on the product first."
                    )
                )

        # ----- Handle original image upload with OSS storage -----
        if "llj_image_original" in vals and vals.get("llj_image_original"):
            # Get the binary data
            bin_data = base64.b64decode(vals["llj_image_original"]) if isinstance(vals["llj_image_original"], str) else vals["llj_image_original"]

            # Get original filename if provided
            original_name = vals.get("llj_image_original_name", "image_original")

            for product in self:
                if not product.llj_id_code:
                    raise UserError(
                        _(
                            "You cannot upload an original image on a product that has no "
                            "ID Code. Set the ID Code on the product first."
                        )
                    )

                # Create attachment with proper context for OSS storage
                # The context will be picked up by ir_attachment._file_write
                if self.env["ir.attachment"]._llj_oss_backend_active():
                    # OSS backend active - use context to set path
                    Attachment = self.env["ir.attachment"].sudo()
                    # Delete old original image attachment if exists
                    old_atts = Attachment.search([
                        ("res_model", "=", "product.template"),
                        ("res_id", "=", product.id),
                        ("name", "=", original_name),
                    ])
                    if old_atts:
                        old_atts.unlink()

                    # Create new attachment with context for proper OSS path
                    Attachment.with_context(
                        llj_id_code=product.llj_id_code,
                        llj_attachment_name=original_name,
                    ).create({
                        "name": original_name,
                        "datas": vals["llj_image_original"],
                        "res_model": "product.template",
                        "res_id": product.id,
                        "mimetype": "image/jpeg" if b"\xff\xd8" in bin_data[:10] else "image/png",
                    })

            # Clear the binary field after processing to avoid double storage
            # when OSS is active. Keep the value when OSS is not active (local storage).
            if self.env["ir.attachment"]._llj_oss_backend_active():
                vals["llj_image_original"] = False

        # ----- Dynamic folder rename when the ID Code changes -----
        if "llj_id_code" in vals:
            new_code = vals["llj_id_code"]  # already normalized to None if empty
            filestore = self.env["ir.attachment"]._filestore()
            Attachment = self.env["ir.attachment"].sudo()
            for product in self:
                old_code = product.llj_id_code
                if not old_code or old_code == new_code:
                    continue
                old_path = os.path.join(filestore, "products", old_code)
                new_path = os.path.join(filestore, "products", new_code)
                # 1) rename the physical folder on disk
                if os.path.isdir(old_path):
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    if os.path.exists(new_path):
                        # merge contents if a folder already exists for new_code
                        for entry in os.listdir(old_path):
                            src = os.path.join(old_path, entry)
                            dst = os.path.join(new_path, entry)
                            if os.path.exists(dst):
                                os.remove(src)
                            else:
                                os.rename(src, dst)
                        os.rmdir(old_path)
                    else:
                        os.rename(old_path, new_path)
                # 2) update every ir.attachment.store_fname that points inside
                #    the old folder, so reads keep working after the rename.
                prefix = "products/%s/" % old_code
                attachments = Attachment.search(
                    [
                        ("res_model", "in", ("product.template", "product.product")),
                        ("res_id", "=", product.id),
                        ("store_fname", "=like", prefix + "%"),
                    ],
                )
                # the =like above can match sibling codes (e.g. AB / ABCD), so
                # filter precisely in python before rewriting the path.
                for att in attachments:
                    if att.store_fname and att.store_fname.startswith(prefix):
                        rel = att.store_fname[len(prefix):]
                        new_fname = "products/%s/%s" % (new_code, rel)
                        self.env.cr.execute(
                            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
                            (new_fname, att.id),
                        )
                if attachments:
                    attachments.invalidate_recordset(["store_fname"])
        return super().write(vals)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    @api.constrains("llj_id_code")
    def _check_llj_id_code(self):
        for product in self:
            code = product.llj_id_code or ""
            if "/" in code or "\\" in code:
                raise ValidationError(
                    _("The ID Code of %s cannot contain slashes.", product.display_name)
                )