import os
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LljOssMigrateWizard(models.TransientModel):
    _name = "llj.oss.migrate.wizard"
    _description = "Migrate Filestore to Alibaba Cloud OSS"

    overwrite = fields.Boolean(
        string="Overwrite existing objects",
        default=False,
        help="If checked, files already present on OSS are re-uploaded.",
    )
    enable_after = fields.Boolean(
        string="Enable OSS backend when done",
        default=True,
        help="Switch ir.attachment reads/writes to OSS once the upload finishes.",
    )
    state = fields.Selection(
        [("draft", "draft"), ("done", "done")], default="draft", required=True
    )
    migrated_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    failed_count = fields.Integer(readonly=True)
    log = fields.Text(readonly=True)

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_migrate(self):
        self.ensure_one()
        Attachment = self.env["ir.attachment"].sudo()
        if Attachment._llj_oss_enabled():
            # We need to read local files, so temporarily read from disk even
            # if OSS is already enabled.
            pass

        filestore = Attachment._filestore()
        dbname = self.env.cr.dbname
        bucket = Attachment._llj_get_bucket()

        migrated = skipped = failed = 0
        log_lines = []

        for root, dirs, files in os.walk(filestore):
            # Skip the filestore garbage-collection spool directory.
            if "checklist" in dirs:
                dirs.remove("checklist")
            for fname_disk in files:
                full_path = os.path.join(root, fname_disk)
                rel = os.path.relpath(full_path, filestore)
                # store_fname always uses forward slashes, even on Windows.
                store_fname = rel.replace(os.sep, "/")
                oss_key = "%s/%s" % (dbname, store_fname)
                try:
                    exists = bucket.object_exists(oss_key)
                    if exists and not self.overwrite:
                        skipped += 1
                        continue
                    with open(full_path, "rb") as fp:
                        bucket.put_object(oss_key, fp.read())
                    migrated += 1
                except Exception as exc:
                    failed += 1
                    log_lines.append("FAILED %s: %s" % (store_fname, exc))
                    _logger.exception("OSS migration failed for %s", store_fname)

        if migrated:
            log_lines.append(
                "Uploaded %d file(s) to OSS under '%s/'." % (migrated, dbname)
            )
        log_lines.append("Skipped %d, failed %d." % (skipped, failed))

        # Reference update: switch the storage backend so Odoo now reads/writes
        # through OSS. ``store_fname`` already references the right object key,
        # so no per-attachment rewrite is needed.
        if self.enable_after and (migrated or skipped) and not failed:
            self.env["ir.config_parameter"].sudo().set_param(
                "llj_oss.enabled", "True"
            )
            log_lines.append("OSS backend enabled.")

        self.write(
            {
                "state": "done",
                "migrated_count": migrated,
                "skipped_count": skipped,
                "failed_count": failed,
                "log": "\n".join(log_lines),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "OSS Migration",
            "res_model": "llj.oss.migrate.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_close(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}
