from odoo import _, api, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        # ----- Check ID Code before allowing variant image updates -----
        # Variant images (image_variant_1920, etc.) are stored on product.product.
        # The ID Code lives on the related product.template, so we check the
        # template's llj_id_code before allowing the save.
        IMAGE_FIELDS = ("image_variant_1920",)
        has_image_update = any(field in vals for field in IMAGE_FIELDS)
        if has_image_update:
            for variant in self:
                template = variant.product_tmpl_id
                if not template.llj_id_code:
                    raise UserError(
                        _(
                            "You cannot edit product images on a product that has no "
                            "ID Code. Set the ID Code on the product template first."
                        )
                    )
        return super().write(vals)