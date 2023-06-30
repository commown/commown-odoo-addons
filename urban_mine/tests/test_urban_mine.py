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
        self.project = self.env.ref("urban_mine.project")
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
        self.env["commown.parcel.type"].create(
            {
                "name": "test parcel",
                "technical_name": "return-0,75-ins300",
                "weight": 0.75,
                "insurance_value": 300,
                "is_return": True,
            }
        )

    def get_tasks(self, partner_id):
        return self.env["project.task"].search(
            [
                ("project_id", "=", self.project.id),
                ("partner_id", "=", partner_id),
            ]
        )

    def get_last_note_message(self, task):
        return [
            m
            for m in task.message_ids
            if list(m.subtype_id.get_xml_id().values()) == ["mail.mt_comment"]
        ][0]

    def check_coupon_message(self, task, campaign):
        "Check message title and the coupon included in the message"
        last_note_msg = self.get_last_note_message(task)
        self.assertIn("Accord de reprise", last_note_msg.subject)
        self.assertIn(task.urban_mine_name(), last_note_msg.subject)
        last_coupon = self.env["coupon.coupon"].search([], limit=1)
        self.assertIn(last_coupon.code, last_note_msg.body)
        self.assertEqual(
            last_coupon.campaign_id,
            self.env.ref("urban_mine." + campaign),
        )

    def test_task_creation(self):
        self.assertEqual(len(self.get_tasks(self.partner.id)), 1)

    def test_task_ok_coupon_only(self):
        task = self.get_tasks(self.partner.id)
        task.update({"stage_id": self.env.ref("urban_mine.stage6")})
        self.check_coupon_message(task, "campaign_coupon_only")

    def test_task_ok_payment(self):
        task = self.get_tasks(self.partner.id)

        fake_meta_data = {"labelResponse": {"parcelNumber": "8R0000000000"}}
        with open(HERE / "fake_label.pdf", "rb") as fobj:
            fake_label_data = fobj.read()

        with mock.patch(
            "odoo.addons.commown_shipping.models.parcel.ship",
            return_value=(fake_meta_data, fake_label_data),
        ) as mocked_ship:
            task.update({"stage_id": self.env.ref("urban_mine.stage2")})

        # Check a return label was created:
        # - the expedition reference is set on the task
        # - the `is_return` arg of the ship function call was `True`
        self.assertEqual(mocked_ship.call_count, 1)
        self.assertIs(mocked_ship.call_args[1]["is_return"], True)
        # A message attached to the task was sent, with the PDF attached
        self.assertTrue(task.message_ids)
        last_note_msg = self.get_last_note_message(task)
        self.assertIn("Accusé Réception", last_note_msg.subject)
        self.assertIn(task.urban_mine_name(), last_note_msg.subject)
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
        task.update({"stage_id": self.env.ref("urban_mine.stage4")})

        # Check results
        invoice = self.env["account.invoice"].search(
            [("reference", "=", task.urban_mine_name())]
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "open")
        self.assertEqual(
            invoice.payment_term_id,
            self.env.ref("account.account_payment_term_15days"),
        )
        self.assertEqual(
            invoice.amount_untaxed,
            self.env.ref("urban_mine.product").standard_price,
        )
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", invoice._name),
                ("res_id", "=", invoice.id),
            ]
        )
        self.assertEqual(len(attachments), 1)
        self.check_coupon_message(task, "campaign_payment")
