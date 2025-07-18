from odoo import models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def _multiply_investments(self, multiplier=10):
        product_ids = (
            self.env["product.template"]
            .with_context(active_test=False)
            .search(
                [
                    ("is_equity", "=", True),
                    ("equity_type", "=", "invest"),
                ]
            )
            .ids
        )

        for invoice in self:
            has_invests = any(
                line
                for line in invoice.invoice_line_ids
                if line.product_id.product_tmpl_id.id in product_ids
            )

            if invoice.amount_residual != 0 or not has_invests:
                continue

            invoice.button_draft()

            pay_term = self.env.ref("commown_investment_sale.investment_payment_term")
            invoice.write({"invoice_payment_term_id": pay_term.id})

            for line in invoice.invoice_line_ids:
                if line.product_id.product_tmpl_id.id in product_ids:
                    line.update({"price_unit": line.price_unit * multiplier})

            invoice.action_post()
