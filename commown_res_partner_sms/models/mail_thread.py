from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post_send_sms_html(self, template, record, *args, **kwargs):
        """Send given mail template as sms, with given record partner language

        The template is rendered with record as the object variable.
        """
        assert template.model == record._name
        template = template.with_context(lang=record.partner_id.lang or "en_US")
        html_message = self.env["mail.template"]._render_template(
            template.body_html, template.model, record.id, post_process=True
        )
        text_message = self.env["ir.fields.converter"].text_from_html(html_message)
        return self.message_post_send_sms(text_message, *args, **kwargs)
