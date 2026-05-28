import datetime

from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task"

    timely_stage_change_datetime = fields.Datetime()
    has_timely_stage_change = fields.Boolean(related="stage_id.has_timely_stage_change")
    timely_stage_dest = fields.Many2one(
        "project.task.type", related="stage_id.timely_stage_dest"
    )

    dest_stage_on_customer_message = fields.Many2one(
        "project.task.type", related="project_id.dest_stage_on_customer_message"
    )

    def write(self, values):
        if "stage_id" in values:
            stage = self.env["project.task.type"].browse(values["stage_id"])

            if stage.has_timely_stage_change:
                values["timely_stage_change_datetime"] = (
                    datetime.datetime.now()
                    + datetime.timedelta(days=stage.timely_stage_change_days)
                )
            else:
                values["timely_stage_change_datetime"] = False

        return super().write(values)
