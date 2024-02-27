from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class Project(models.Model):
    _inherit = "project.project"

    can_write = fields.Boolean(
        compute="_compute_can_write",
        store=False,
    )

    def _compute_can_write(self):
        can_write_record_ids = self._filter_access_rules("write").ids
        for record in self:
            record.can_write = record.id in can_write_record_ids

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        if not self.env.user.has_group("project.group_project_manager"):
            vals["privacy_visibility"] = "followers"
        return super().create(vals)

    @api.multi
    def write(self, vals):

        if not self.env.user.has_group("project.group_project_manager"):
            if "privacy_visibility" in vals:
                raise AccessError(
                    _("Need to be a project manager to change a project's visibility.")
                )

            if "user_id" in vals:
                raise AccessError(
                    _("Need to be a project manager to change a project's manager.")
                )

        return super().write(vals)
