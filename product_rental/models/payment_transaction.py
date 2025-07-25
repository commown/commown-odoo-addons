from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def autopay_contract_invoices(self):
        self.ensure_one()

        for invoice in self.invoice_ids:
            for contract in invoice.mapped(
                "invoice_line_ids.contract_line_id.contract_id"
            ):
                if contract.payment_mode_id:
                    token = (
                        contract.payment_token_id
                        or contract.partner_id.payment_token_id
                    )
                    register_payment = (
                        self.env["account.payment.register"]
                        .with_context(
                            active_ids=invoice.ids, active_model=invoice._name
                        )
                        .create(
                            {
                                "journal_id": contract.payment_mode_id.fixed_journal_id.id,
                                "payment_token_id": token.id,
                            }
                        )
                    )
                    register_payment._create_payments()
