from odoo import _, api, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _get_invoice_key_cols(self):
        """Do not consider user_id as a key to merge invoices as we don't use
        the user_id and it is not significant for the matter of auto payment.
        """
        key_cols = super(AccountInvoice, self)._get_invoice_key_cols()
        try:
            key_cols.remove("user_id")
        except ValueError:
            pass
        return key_cols

    @api.multi
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
                l
                for l in invoice.invoice_line_ids
                if l.product_id.product_tmpl_id.id in product_ids
            )

            if invoice.residual != 0 or not has_invests:
                continue

            invoice.payment_move_line_ids
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

    def _invoice_merge_auto_pay_invoice_job(self):
        result = super()._invoice_merge_auto_pay_invoice_job()
        if (
            self.state == "paid"
            and self.sent is False
            and self.partner_id.type == "invoice"
            and self.partner_id.email
        ):
            mail_template = self.env.ref(
                "account.email_template_edi_invoice",
                raise_if_not_found=False,
            )
            if mail_template:
                mail_template.send_mail(self.id)
            self.with_context(mail_post_autofollow=True)
            self.sent = True
            self.message_post(body=_("Invoice sent"))

        return result
