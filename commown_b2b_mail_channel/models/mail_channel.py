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

    @api.depends("partner_companies")
    def _compute_partner_company(self):
        for rec in self.filtered("partner_companies"):
            rec.partner_company = rec.partner_companies[0]
            rec.partner_company.set_support_channel_name(self)

    @api.onchange("partner_company")
    def onchange_partner_companies_set_name(self):
        self.partner_company.set_support_channel_name(self)

    def _inverse_partner_company(self):
        for rec in self:
            chan = rec
            new_company = rec.partner_company

            self.env["res.partner"].search([("mail_channel_id", "=", rec.id)]).update(
                {"mail_channel_id": False}
            )

            chan.partner_companies = new_company

    def remove_partners_but_employees(self):
        employee_partners = self.env.ref("commown_user_roles.employee").user_ids.mapped(
            "partner_id"
        )
        self.env["mail.channel.member"].search(
            [
                ("channel_id", "=", self.id),
                ("partner_id", "not in", employee_partners.ids),
            ]
        ).unlink()
