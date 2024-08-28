from odoo import api, fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    company_ids = fields.One2many(
        "res.partner",
        inverse_name="mail_channel_id",
        domain=[("is_company", "=", "True")],
    )

    company_id = fields.Many2one(
        "res.partner",
        string="Support channel of",
        compute="_compute_company_id",
        inverse="_inverse_company_id",
        domain=[("is_company", "=", "True")],
        store=False,
    )

    @api.depends("company_ids")
    def _compute_company_id(self):
        for rec in self.filtered("company_ids"):
            rec.company_id = rec.company_ids[0]

    def _inverse_company_id(self):
        for rec in self:
            rec.company_ids = rec.company_id
