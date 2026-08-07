from odoo import fields, models


class Project(models.Model):
    _name = "project.project"
    _inherit = [
        "project.project",
        "commown_devices.picking_order_parent_mixin",
    ]

    device_tracking = fields.Boolean("Use for device tracking?", default=False)

    show_related_move_lines = fields.Boolean("Show related move lines?", default=False)
