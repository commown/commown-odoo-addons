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
        compute="_compute_automated_control_id",
        readonly=True,
    )

    @api.depends("automated_control_ids")
    def _compute_automated_control_id(self):
        no_control_ids = []
        for rec in self:
            if rec.automated_control_ids:
                rec.automated_control_id = rec.automated_control_ids[0]
            else:
                no_control_ids.append(rec.id)

        self.env["base.automation"].browse(no_control_ids).automated_control_id = False

    def delete_last_line(self):
        self.action_server_id.delete_last_line()
