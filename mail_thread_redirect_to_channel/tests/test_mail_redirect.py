from odoo_test_helper import FakeModelLoader

from odoo.tests import TransactionCase


class MailThreadRedirectTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        from .models import Redirect_DummyModel

        cls.loader.update_registry((Redirect_DummyModel,))

        cls.acl = cls.env["ir.model.access"].create(
            {
                "name": "dummy.model.access",
                "model_id": cls.env.ref(
                    "mail_thread_redirect_to_channel.model_dummy_model"
                ).id,
                "perm_read": 1,
                "perm_write": 1,
                "perm_create": 1,
                "perm_unlink": 1,
            }
        )

        cls.user_internal = cls.env.ref("base.user_demo")
        cls.user_portal = cls.env.ref("base.demo_user0")

        cls.channel = cls.env["mail.channel"].create({"name": "Test Channel"})
        cls.dummy_1, cls.dummy_2 = cls.env["dummy.model"].create(
            [
                {"name": "Dummy 1", "dummy_boolean": True},
                {"name": "Dummy 2", "dummy_boolean": False},
            ]
        )

        cls.redirect = cls.env["mail.thread.redirect"].create(
            {
                "name": "Redirection",
                "model_id": cls.env["ir.model"]._get("dummy.model").id,
                "target_channel_id": cls.channel.id,
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.acl.unlink()
        cls.loader.restore_registry()
        return super().tearDownClass()

    def _post_message(self, rec, body, user, message_type="email"):
        rec.with_user(user).message_post(
            body=body,
            email_from=user.email,
            subject="Test subject",
            message_type=message_type,
            subtype_xml="mail.mt_comment",
        )

    def test_redirect_message_from_rec_to_channel(self):
        self.redirect.filter_domain = "[('dummy_boolean', '=', True)]"

        self._post_message(
            self.dummy_1, "Redirect test n°1 - Should redirect", self.user_internal
        )
        self._post_message(
            self.dummy_2,
            "Redirect test n°2 - Shouldn't redirect",
            self.user_internal,
        )

        chan_message = self.channel.message_ids
        self.assertEqual(len(chan_message), 1)

        self.assertIn("test n°1", chan_message.body)
        self.assertNotIn("test n°2", chan_message.body)

        expected_link = f"/web#model={self.dummy_1._name}&amp;id={self.dummy_1.id}"
        self.assertIn(expected_link, chan_message.body)

    def test_redirect_with_markup_body(self):
        "The body of the channel post should be properly transcribed"
        body_w_tags = "<b>Redirect with HTML tag</b>"

        self._post_message(self.dummy_1, body_w_tags, self.user_internal)

        chan_message = self.channel.message_ids
        self.assertEqual(len(chan_message), 1)

        self.assertIn(body_w_tags, chan_message.body)

    def test_redirect_only_portal_users(self):
        # Case 1: Only portal user messages are redirected
        self.redirect.only_portal_users = True

        self._post_message(
            self.dummy_1, "Redirect test n°1 - Should redirect", self.user_portal
        )
        self._post_message(
            self.dummy_1, "Redirect test n°2 - Shouldn't redirect", self.user_internal
        )

        chan_message_1 = self.channel.message_ids
        self.assertEqual(len(chan_message_1), 1)

        self.assertIn("test n°1", chan_message_1.body)
        self.assertNotIn("test n°2", chan_message_1.body)

        # Case 2: All messages are redirected
        self.redirect.only_portal_users = False

        self._post_message(
            self.dummy_1, "Redirect test n°1 - Should redirect", self.user_portal
        )
        self._post_message(
            self.dummy_1, "Redirect test n°2 - Should redirect", self.user_internal
        )
        new_chan_messages = self.channel.message_ids - chan_message_1
        self.assertEqual(len(new_chan_messages), 2)
        self.assertIn("Redirect test", new_chan_messages[0].body)
        self.assertIn("Redirect test", new_chan_messages[1].body)
