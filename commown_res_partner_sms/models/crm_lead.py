from odoo import models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    def action_sms_lead_doc_reminder(self):
        phone = self.partner_id.get_mobile_phone()
        if phone:
            # Send the SMS
            template = self.env.ref("commown.sms_template_lead_doc_reminder")
            message = self.env["ir.fields.converter"].text_from_html(template.body_html)
            self.message_post_send_sms(message, numbers=[phone], log_error=True)
