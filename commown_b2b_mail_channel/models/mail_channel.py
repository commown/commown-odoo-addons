from odoo import api, fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    partner_companies = fields.One2many(
        "res.partner",
        inverse_name="mail_channel_id",
        domain=[("is_company", "=", "True")],
    )

    partner_company = fields.Many2one(
        "res.partner",
        string="Support channel of",
        compute="_compute_partner_company",
        inverse="_inverse_partner_company",
        domain=[("is_company", "=", "True")],
        store=False,
    )

    @api.depends("company_ids")
    def _compute_company_id(self):
        for rec in self.filtered("company_ids"):
            rec.company_id = rec.company_ids[0]

    def _inverse_partner_company(self):
        for rec in self:
            chan = rec
            new_company = rec.partner_company

            self.env["res.partner"].search([("mail_channel_id", "=", rec.id)]).update(
                {"mail_channel_id": False}
            )

            chan.partner_companies = new_company
