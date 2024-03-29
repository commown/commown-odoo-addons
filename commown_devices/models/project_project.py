from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    device_tracking = fields.Boolean("Use for device tracking?", default=False)
