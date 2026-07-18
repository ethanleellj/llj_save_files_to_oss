from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    llj_oss_enabled = fields.Boolean(
        string="Use Alibaba Cloud OSS",
        config_parameter="llj_oss.enabled",
        help="When enabled, attachment binary content is read from / written "
        "to Alibaba Cloud OSS instead of the local filestore.",
    )
    llj_oss_access_key_id = fields.Char(
        string="OSS Access Key ID",
        config_parameter="llj_oss.access_key_id",
    )
    llj_oss_access_key_secret = fields.Char(
        string="OSS Access Key Secret",
        config_parameter="llj_oss.access_key_secret",
    )
    llj_oss_endpoint = fields.Char(
        string="OSS Endpoint",
        config_parameter="llj_oss.endpoint",
        placeholder="https://oss-cn-hangzhou.aliyuncs.com",
    )
    llj_oss_bucket_name = fields.Char(
        string="OSS Bucket Name",
        config_parameter="llj_oss.bucket_name",
    )
    llj_oss_cdn_domain = fields.Char(
        string="OSS CDN Domain (optional)",
        config_parameter="llj_oss.cdn_domain",
        placeholder="https://cdn.example.com",
    )

    @api.onchange("llj_oss_enabled")
    def _onchange_llj_oss_enabled(self):
        if self.llj_oss_enabled and not (
            self.llj_oss_access_key_id
            and self.llj_oss_access_key_secret
            and self.llj_oss_endpoint
            and self.llj_oss_bucket_name
        ):
            return {
                "warning": {
                    "title": "Missing configuration",
                    "message": (
                        "OSS is enabled but some credentials are missing. "
                        "Fill in the Access Key ID, Secret, Endpoint and "
                        "Bucket Name, and run the migration wizard to upload "
                        "the existing local files."
                    ),
                }
            }
