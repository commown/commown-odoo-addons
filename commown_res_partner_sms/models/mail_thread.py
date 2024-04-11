from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post_send_sms_html(self, html_message, *args, **kwargs):
        text_message = self.env["ir.fields.converter"].text_from_html(html_message)
        return self.message_post_send_sms(text_message, *args, **kwargs)
