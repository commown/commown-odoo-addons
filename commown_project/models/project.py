from odoo import _, api, models
from odoo.exceptions import AccessError


class Project(models.Model):
    _inherit = "project.project"

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
