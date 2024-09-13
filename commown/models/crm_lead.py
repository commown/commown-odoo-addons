from datetime import date

from odoo import api, fields, models

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    contract_id = fields.Many2one(
        domain="[('commercial_partner_id', '=', commercial_partner_id)]",
    )

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        result = super().create(vals)
        if not result.contract_id:
            result.send_email_on_delivery = False
        return result

    @api.multi
    def delivery_perform_actions(self):
        super().delivery_perform_actions()
        today = date.today()
        for record in self.filtered("contract_id"):
            # Current method may be called by users not allowed to update
            # contracts, so we use sudo here:
            contract = record.contract_id.sudo()
            # Do not restart contract that have already started
            if contract.date_start and contract.date_start <= today:
                continue
            contract.date_start = record.delivery_date

    def _action_send_sms_doc_reminder(self):
        template = self.env.ref("commown.sms_template_lead_doc_reminder")
        country_code = self.partner_id.country_id.code
        phone = normalize_phone(self.partner_id.get_mobile_phone(), country_code)
        # Send the SMS
        self.message_post_send_sms_html(template, self, numbers=[phone], log_error=True)
