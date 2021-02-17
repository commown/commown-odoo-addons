from odoo import models, fields


class CommownProjectIssue(models.Model):
    _name = "project.issue"
    _inherit = [
        "project.issue",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "project_id"

    delivery_tracking = fields.Boolean(
        'Delivery tracking', related='project_id.delivery_tracking')
