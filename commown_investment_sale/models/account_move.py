from odoo import models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def _multiply_investments(self, multiplier=10):
        "Multiply by `multiplier` the unit price of investment product invoice lines"

        pt_model = self.env["product.template"].with_context(active_test=False)
        invest_products = pt_model.search(
            [("is_equity", "=", True), ("equity_type", "=", "invest")]
        )

        pay_term = self.env.ref("commown_investment_sale.investment_payment_term")

        for invoice in self:
            if invoice.amount_residual != 0:
                continue

            invest_lines = invoice.invoice_line_ids.filtered(
                lambda l: l.product_id.product_tmpl_id.id in invest_products.ids
            )

            if not invest_lines:
                continue

            invoice.button_draft()
            invoice.write({"invoice_payment_term_id": pay_term.id})
            for line in invest_lines:
                line.update({"price_unit": line.price_unit * multiplier})
            invoice.action_post()
