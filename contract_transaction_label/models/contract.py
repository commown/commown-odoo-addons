import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "contract.contract"

    transaction_label = fields.Text(
        string="Payment label",
        default="#INV#",
        help=(
            "Label to be used for the bank payment. "
            "Possible markers: #START#, #END#, #INV# (invoice number)"
        ),
    )

    def _format_transaction_label(self, invoice, last_date_invoiced):
        self.ensure_one()
        lang = self.env["res.lang"].search([("code", "=", self.partner_id.lang)])
        date_format = lang.date_format or "%m/%d/%Y"
        label = self.transaction_label
        label = label.replace("#START#", invoice.date_invoice.strftime(date_format))
        label = label.replace("#END#", last_date_invoiced.strftime(date_format))
        label = label.replace("#INV#", invoice.number)
        return label

    def _pay_invoice(self, invoice):
        """Insert custom payment transaction label into the context
        before executing the standard payment process."""
        if self.transaction_label:
            last_date_invoiced = max(
                invoice.mapped("invoice_line_ids.contract_line_id.last_date_invoiced")
            )
            label = self._format_transaction_label(invoice, last_date_invoiced)
            _logger.debug("Bank label for invoice %s: %s", invoice.number, label)
            self = self.with_context(slimpay_payin_label=label)
        return super()._pay_invoice(invoice)
