import logging
from datetime import date

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class CommownPartner(models.Model):
    _inherit = "res.partner"

    parent_payment_token_id = fields.Many2one(
        string="Parent Payment token", related="parent_id.payment_token_id"
    )

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
                ("move_type", "=", "out_invoice"),
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
