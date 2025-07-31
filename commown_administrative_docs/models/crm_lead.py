from odoo import models

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    def _action_send_sms_doc_reminder(self):
        template = self.env.ref(
            "commown_administrative_docs.sms_template_lead_doc_reminder"
        )
        country_code = self.partner_id.country_id.code
        phone = normalize_phone(self.partner_id.get_mobile_phone(), country_code)
        # Send the SMS
        self.send_sms_from_template(template, self, numbers=[phone], log_error=True)
