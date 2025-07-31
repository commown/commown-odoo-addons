import logging
from datetime import date

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CommownPartner(models.Model):
    _inherit = "res.partner"

    def _default_country(self):
        return self.env["res.company"]._company_default_get().country_id

    country_id = fields.Many2one(default=_default_country)

    parent_payment_token_id = fields.Many2one(
        string="Parent Payment token", related="parent_id.payment_token_id"
    )

    @api.model
    def signup_retrieve_info(self, token):
        """Override auth_signup method for compat with partner_firstname:
        retrieve first- and last- name for the reset password form.
        """
        partner = self._signup_retrieve_partner(token, raise_exception=True)
        res = {"db": self.env.cr.dbname}
        if partner.signup_valid:
            res["token"] = token
            res["firstname"] = partner.firstname
            res["lastname"] = partner.lastname
        if partner.user_ids:
            res["login"] = partner.user_ids[0].login
        else:
            res["email"] = res["login"] = partner.email or ""
        return res

    def action_set_as_invoice_recipient(self):
        self.ensure_one()

        contracts = self.env["contract.contract"].search(
            [
                ("partner_id", "=", self.parent_id.id),
                "|",
                ("date_end", ">=", date.today()),
                "&",
                ("date_end", "=", False),
                ("recurring_next_date", "!=", False),
            ]
        )
        contracts.update({"invoice_partner_id": self.id})

        invoices = self.env["account.move"].search(
            [
                ("type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("partner_id", "=", self.parent_id.id),
                ("line_ids.contract_line_id", "!=", False),
            ]
        )
        invoices.update({"partner_id": self.id})

        msg = _("Modified %(cs)d contracts and %(invs)d invoices") % {
            "cs": len(contracts),
            "invs": len(invoices),
        }
        self.env.user.notify_success(message=msg, title=_("Information"), sticky=True)
        return True
