from unittest import mock

from odoo.tests import tagged

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class CrmLeadTC(RentalSaleOrderTC):
    def test_action_send_sms_doc_reminder(self):
        fr = self.env.ref("base.fr")

        lead = self.env.ref("crm.crm_case_22")
        lead.partner_id.update({"country_id": fr.id, "phone": "+33747397654"})
        template = self.env.ref(
            "commown_administrative_docs.sms_template_lead_doc_reminder"
        )
        country_code = lead.partner_id.country_id.code
        partner_mobile = normalize_phone(
            lead.partner_id.get_mobile_phone(),
            country_code,
        )
        with mock.patch(
            "odoo.addons.commown_res_partner_sms.models."
            "mail_thread.MailThread.message_post_send_sms_html"
        ) as post_message:
            lead._action_send_sms_doc_reminder()
            post_message.assert_called_once_with(
                template,
                lead,
                numbers=[partner_mobile],
                log_error=True,
            )
