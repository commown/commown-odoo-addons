from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def send_sms_from_template(self, template, record, *args, **kwargs):
        """Send given template as sms, with given record partner language

        The template is rendered with record as the object variable.
        """
        assert template.model == record._name
        template = template.with_context(lang=record.partner_id.lang or "en_US")
        body = self.env["sms.template"]._render_template(
            template.body, record._name, [record.id]
        )[record.id]
        subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        return self.message_post(
            message_type="sms", body=body, subtype_id=subtype_id, *args, **kwargs
        )
