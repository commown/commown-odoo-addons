from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    has_timely_stage_change = fields.Boolean()
    timely_stage_change_days = fields.Integer(
        help=(
            "This number can only be set as strictly positive, "
            "otherwise, any task moved into this stage would be "
            "moved directly to the defined destination stage."
        ),
    )
    timely_stage_dest = fields.Many2one(
        "project.task.type", domain="[('project_ids', '=', project_ids)]"
    )

    @api.constrains(
        "has_timely_stage_change", "timely_stage_change_days", "timely_stage_dest"
    )
    def _check_timely_stage_change_fields(self):
        for stage in self:
            if stage.has_timely_stage_change:
                if not stage.timely_stage_dest:
                    raise ValidationError(
                        _(
                            "You must set a destination stage for the passive change, "
                            "as the passive change is active on this stage."
                        )
                    )

                if stage.timely_stage_change_days <= 0:
                    raise ValidationError(
                        _(
                            "You must set a strictly positive number of days! "
                            "(or else, any task would be immediatly moved after being set in this stage)"
                        )
                    )
