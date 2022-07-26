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
                    payment = self.env["account.payment"].create(
                        {
                            "company_id": 1,  # ourselves!
                            "partner_id": contract.partner_id.id,
                            "partner_type": "customer",
                            "state": "draft",
                            "payment_type": "inbound",
                            "journal_id": contract.payment_mode_id.fixed_journal_id.id,
                            "payment_method_id": contract.payment_mode_id.payment_method_id.id,
                            "amount": self.amount,
                            "payment_transaction_id": self.id,
                            "invoice_ids": [(6, 0, [invoice.id])],
                        }
                    )
                    payment.post()
