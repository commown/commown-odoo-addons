from odoo import api, fields, models


class CommownProjectTask(models.Model):
    _name = "project.task"
    _inherit = [
        "project.task",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "project_id"
    _delivery_tracking_stage_parent_rel = "project_ids"

    delivery_tracking = fields.Boolean(
        "Delivery tracking", related="project_id.delivery_tracking"
    )

    @api.multi
    def _attachment_from_label(self, name, meta_data, label_data):
        self.initialize_expedition_data(meta_data["labelResponse"]["parcelNumber"])
        return super()._attachment_from_label(name, meta_data, label_data)
