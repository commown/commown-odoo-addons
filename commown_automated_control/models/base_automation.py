from odoo import api, fields, models


class BaseAutomation(models.Model):
    _inherit = "base.automation"

    automated_control_ids = fields.One2many(
        "commown_automated_control.automated_control",
        string="Controls",
        inverse_name="base_automation_id",
    )

    automated_control_id = fields.Many2one(
        "commown_automated_control.automated_control",
        compute="_compute_automated_contol_id",
        readonly=True,
    )

    @api.depends("automated_control_ids")
    def _compute_automated_contol_id(self):
        for rec in self.filtered("automated_control_ids"):
            rec.automated_control_id = rec.automated_control_ids[0]
