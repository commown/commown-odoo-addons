from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task"

    timely_stage_change_datetime = fields.Datetime()
    has_timely_stage_change = fields.Boolean(related="stage_id.has_timely_stage_change")
    timely_stage_dest = fields.Many2one(
        "project.task.type", related="stage_id.timely_stage_dest"
    )
