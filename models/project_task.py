from odoo import models, api


class CommownProjectTask(models.Model):
    _name = "project.task"
    _inherit = [
        "project.task",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "project_id"
