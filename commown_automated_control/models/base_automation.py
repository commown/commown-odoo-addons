from odoo import fields, models


class BaseAutomation(models.Model):
    _inherit = "base.automation"

    automated_control_ids = fields.One2many(
        "commown_automated_control.automated_control",
        string="Controls",
        inverse_name="base_automation_id",
    )
