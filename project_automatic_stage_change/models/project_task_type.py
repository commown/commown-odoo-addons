from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    has_timely_stage_change = fields.Boolean()
    timely_stage_change_days = fields.Integer()
    timely_stage_dest = fields.Many2one(
        "project.task.type", domain="[('project_ids', '=', id)]"
    )
