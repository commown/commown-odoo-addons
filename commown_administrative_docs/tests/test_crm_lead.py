from odoo.tests import tagged

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class CrmLeadTC(RentalSaleOrderTC):
    def test_action_send_sms_doc_reminder(self):
        fr = self.env.ref("base.fr")

        lead = self.env.ref("crm.crm_case_22")
        lead.partner_id.update({"country_id": fr.id, "phone": "+33747397654"})
        country_code = lead.partner_id.country_id.code
        partner_mobile = normalize_phone(
            lead.partner_id.get_mobile_phone(),
            country_code,
        )

        lead._action_send_sms_doc_reminder()

        # Check whether a SMS text was created, with the partner mobile as number
        lead_sms = lead.message_ids.filtered(lambda m: m.message_type == "sms")
        self.assertTrue(lead_sms)
        self.assertEqual(lead_sms.notification_ids.sms_number, partner_mobile)
