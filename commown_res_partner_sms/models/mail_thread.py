from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post_send_sms_html(self, template, record_id, *args, **kwargs):
        html_message = self.env["mail.template"]._render_template(
            template.body_html, template.model, record_id, post_process=True
        )
        text_message = self.env["ir.fields.converter"].text_from_html(html_message)
        return self.message_post_send_sms(text_message, *args, **kwargs)
