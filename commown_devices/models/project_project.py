from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    device_tracking = fields.Boolean("Use for device tracking?", default=False)

    show_related_move_lines = fields.Boolean("Show related move lines?", default=False)

    add_tasks_to_device_history = fields.Boolean(
        string="Add project tasks to device history?",
        default=False,
    )
