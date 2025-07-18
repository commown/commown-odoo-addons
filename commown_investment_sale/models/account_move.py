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

            if invoice.residual != 0 or not has_invests:
                continue

            invoice.payment_move_line_ids.remove_move_reconcile()
            self.env.cache.invalidate()

            invoice.action_invoice_cancel()
            self.env.cache.invalidate()

            invoice.action_invoice_draft()
            investment_payment_term = self.env.ref("commown.investment_payment_term")
            invoice.write({"payment_term_id": investment_payment_term.id})
            self.env.cache.invalidate()

            for line in invoice.invoice_line_ids:
                if line.product_id.product_tmpl_id.id in product_ids:
                    line.update({"price_unit": line.price_unit * multiplier})

            invoice.action_invoice_open()
            self.env.cache.invalidate()
