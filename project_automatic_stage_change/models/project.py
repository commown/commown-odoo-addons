from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.project"

    dest_stage_on_customer_message = fields.Many2one(
        "project.task.type", domain="[('project_ids', '=', id)]"
    )
