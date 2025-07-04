# Copyright (C) 2019 - Today: Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.queue_job.job import identity_exact

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_merge = fields.Boolean(
        # Override label and help only
        string="Pay automatically",
        help="Pay automatically at partner's next merge date",
    )

    @api.constrains("auto_merge", "payment_mode_id")
    def _check_auto_merge(self):
        for inv in self:
            if inv.auto_merge and not inv.payment_mode_id:
                raise models.ValidationError(
                    _("Payment mode is needed to auto pay an invoice")
                )

    @api.model
    def _invoice_merge_auto_pay_invoice_job(self):
        """Open the invoice and post a payment"""
        self.ensure_one()
        _logger.info(
            "_invoice_merge_auto_pay_invoice_job executed for invoice %d", self.id
        )
        if self.payment_state != "paid":  # Avoid crash if, e.g. amount == 0
            self._invoice_merge_payment()

    @api.model
    def _invoice_merge_payment(self):
        """Post current invoice, pay it and return the account.payment

        Raises ValidationError if the parther has no payment token.
        """
        self.ensure_one()

        token = self.partner_id.payment_token_id
        if not token:
            raise ValidationError(
                _("No payment token for invoice id %(id)s (%(num)s)")
                % {"id": self.id, "num": self.name}
            )

        self.action_post()

        register_payment = (
            self.env["account.payment.register"]
            .with_context(active_ids=self.ids, active_model=self._name)
            .create(
                {
                    "journal_id": self.payment_mode_id.fixed_journal_id.id,
                    "payment_token_id": token.id,
                }
            )
        )
        return register_payment._create_payments()

    @api.model
    def _cron_invoice_merge(self, merge_date=None):
        """Automatically pay invoices that were either:

        - the result invoice of a merge
        - or a candidate for a merge but were not merged
          (for instance because they were unique for the merge key)
        """

        invoices, merge_infos = super()._cron_invoice_merge(merge_date)
        for new_inv_id in merge_infos:
            new_inv = self.env["account.move"].browse(new_inv_id)
            if new_inv.move_type == "out_invoice":
                _logger.info(
                    "Automatically paying merged invoice %s (from %s)",
                    new_inv.id,
                    merge_infos[new_inv.id],
                )
                new_inv.with_delay(
                    identity_key=identity_exact
                )._invoice_merge_auto_pay_invoice_job()

        merged_invoice_ids = {
            inv_id for inv_ids in list(merge_infos.values()) for inv_id in inv_ids
        }
        for inv in invoices:
            if inv.move_type == "out_invoice" and inv.id not in merged_invoice_ids:
                _logger.info("Automatically paying non-merged inv %s", inv.id)
                inv.with_delay(
                    identity_key=identity_exact
                )._invoice_merge_auto_pay_invoice_job()

        return invoices, merge_infos
