import requests_mock
from odoo_test_helper import FakeModelLoader

from odoo.tests.common import SavepointCase


class MailThreadTC(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a fake model to test abstract model MailThread
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import MailThreadTest

        cls.loader.update_registry((MailThreadTest,))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_send_sms_from_template(self):
        mail_thread = self.env["mail.thread.test"].create({})
        user = self.env.ref("base.user_demo")
        user_model = self.env["ir.model"]._get(user._name)
        template = self.env["sms.template"].create(
            {"body": r"TEST message to {{object.name}}", "model_id": user_model.id}
        )

        message_num = len(mail_thread.message_ids)
        with requests_mock.Mocker() as rm:
            rm.get("https://www.ovh.com/cgi-bin/sms/http2sms.cgi", text="OK")
            mail_thread.send_sms_from_template(
                template, user, sms_numbers=["0600070022"]
            )

        self.assertEqual(len(mail_thread.message_ids), message_num + 1)
        sms = mail_thread.message_ids[0]
        self.assertEqual(sms.subtype_id, self.env.ref("mail.mt_note"))

        expected_message = "<p>TEST message to %s</p>" % user.name
        self.assertEqual(expected_message, sms.body)

        # Check raise when object model is different than template one
        partner_model = self.env["ir.model"]._get(user.partner_id._name)
        template.model_id = partner_model
        with self.assertRaises(AssertionError):
            mail_thread.send_sms_from_template(
                template, user, sms_numbers=["0600070022"]
            )
