from odoo import _, api, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_invoice_key_cols(self):
        """Do not consider user_id as a key to merge invoices as we don't use
        the user_id and it is not significant for the matter of auto payment.
        """
        key_cols = super()._get_invoice_key_cols()
        return [key_col for key_col in key_cols if key_col != "user_id"]

    def _invoice_merge_auto_pay_invoice_job(self):
        result = super()._invoice_merge_auto_pay_invoice_job()
        if (
            self.payment_state == "paid"
            and self.is_move_sent is False
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
            self.is_move_sent = True
            self.message_post(body=_("Invoice sent"))

        return result
