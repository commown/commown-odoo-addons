from odoo import fields, models


class CommownProjectTask(models.Model):
    _name = "project.task"
    _inherit = [
        "project.task",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = "project_id"
    _delivery_tracking_stage_parent_rel = "project_ids"

    delivery_tracking = fields.Boolean(
        "Delivery tracking", related="project_id.delivery_tracking"
    )
