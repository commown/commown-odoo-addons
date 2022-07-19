from base64 import b64decode
from pathlib import Path

import mock

from odoo.tests.common import TransactionCase, at_install, post_install

HERE = (Path(__file__) / "..").resolve()


@at_install(False)
@post_install(True)
class TestRegistration(TransactionCase):
    def setUp(self):
        super(TestRegistration, self).setUp()
        self.team = self.env.ref("urban_mine.urban_mine_managers")
        self.partner = self.env["res.partner"].create(
            {
                "name": "Elie A",
                "email": "elie@commown.fr",
                "street": "2 rue de Rome",
                "zip": "67000",
                "city": "Strasbourg",
                "country_id": self.env.ref("base.fr").id,
                "supplier": True,
                "from_urban_mine": True,
            }
        )

    def get_leads(self, partner_id):
        return self.env["crm.lead"].search(
            [
                ("team_id", "=", self.team.id),
                ("partner_id", "=", partner_id),
            ]
        )

    def get_last_note_message(self, lead):
        return [
            m
            for m in lead.message_ids
            if list(m.subtype_id.get_xml_id().values()) == ["mail.mt_comment"]
        ][0]

    def test_opportunity_creation(self):
        self.assertEqual(len(self.get_leads(self.partner.id)), 1)

    def test_opportunity_ok(self):
        lead = self.get_leads(self.partner.id)

        fake_meta_data = {"labelResponse": {"parcelNumber": "8R0000000000"}}
        with open(HERE / "fake_label.pdf", "rb") as fobj:
            fake_label_data = fobj.read()

        with mock.patch(
            "odoo.addons.commown_shipping.models.parcel.ship",
            return_value=(fake_meta_data, fake_label_data),
        ) as mocked_ship:
            lead.update({"stage_id": self.env.ref("urban_mine.stage2")})

        # Check a return label was created:
        # - the expedition reference is set on the lead
        # - the `is_return` arg of the ship function call was `True`
        self.assertEqual(mocked_ship.call_count, 1)
        self.assertIs(mocked_ship.call_args[1]["is_return"], True)
        # A message attached to the lead was sent, with the PDF attached
        self.assertTrue(lead.message_ids)
        last_note_msg = self.get_last_note_message(lead)
        self.assertIn("Accusé Réception", last_note_msg.subject)
        self.assertIn("COMMOWN-MU-%d" % lead.id, last_note_msg.subject)
        attachment = last_note_msg.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.mimetype, "application/pdf")
        self.assertEqual(b64decode(last_note_msg.attachment_ids.datas), fake_label_data)

        # Next step: registration is validated
        # The invoice and coupon code must be sent by email

        # Use a fake auto-invoice report to avoid installing its dependencies
        report = self.env.ref("urban_mine.report_autoinvoice")
        report.py3o_template_fallback = "tests/fake_report.odt"

        # Launch test
        lead.update({"stage_id": self.env.ref("urban_mine.stage4")})

        # Check results
        invoice = self.env["account.invoice"].search(
            [("reference", "=", "COMMOWN-MU-%d" % lead.id)]
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "open")
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", invoice._name),
                ("res_id", "=", invoice.id),
            ]
        )
        self.assertEqual(len(attachments), 1)
        last_note_msg = self.get_last_note_message(lead)
        self.assertIn("Accord de reprise", last_note_msg.subject)
        self.assertIn("COMMOWN-MU-%d" % lead.id, last_note_msg.subject)
        last_coupon = self.env["coupon.coupon"].search([])[0]
        self.assertIn(last_coupon.code, last_note_msg.body)
