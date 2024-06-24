from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    portal_visibility_extend_to_group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Portal visibility extension groups",
        help=(
            "If not empty, portal users will view this project's tasks only if they"
            " belong to one of these groups and have a colleague following the task."
        ),
        domain=lambda self: [
            (
                "category_id",
                "=",
                self.env.ref("base.module_category_manager_customer").id,
            ),
        ],
    )
