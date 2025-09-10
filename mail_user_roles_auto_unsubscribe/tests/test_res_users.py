from odoo.tests import Form, TransactionCase


class UserUnsubscribeChannelTC(TransactionCase):
    @classmethod
    def _create_group(cls, name):
        return cls.env["res.groups"].create({"name": name})

    @classmethod
    def _create_role(cls, name, group, user):
        "Create a role from name and associated group and add the user in it."
        role = cls.env["res.users.role"].create(
            {
                "name": name,
                "group_id": group.id,
                "line_ids": [(0, 0, {"user_id": user.id})],
            }
        )
        return role

    def find_role_rec_index(self, role_rec, records):
        """
        This helper serves to find the index of the role_rec
        in the O2MProxy._record list of dicts.
        """
        role_line = self.env["res.users.role.line"].search(
            [
                ("role_id.id", "=", role_rec.id),
                ("user_id.id", "=", self.test_user_1.id),
            ]
        )

        return records.index([r for r in records if r["id"] == role_line.id][0])

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_user_1 = cls.env["res.users"].create(
            {
                "name": "Test user 1",
                "login": "test",
            }
        )
        cls.subscribed_group1 = cls._create_group("Subcribed group 1")
        cls.subscribed_group2 = cls._create_group("Subcribed group 2")
        cls.nonsubscribed_group = cls._create_group("Non Subscribed Group")

        cls.subscribed_role1 = cls._create_role(
            "Subscribed role 1",
            cls.subscribed_group1,
            cls.test_user_1,
        )
        cls.subscribed_role2 = cls._create_role(
            "Subscribed role 2",
            cls.subscribed_group2,
            cls.test_user_1,
        )
        cls.nonsubscribed_role = cls._create_role(
            "Nonsubscribed role",
            cls.nonsubscribed_group,
            cls.test_user_1,
        )

        subscribed_group_ids = [
            cls.subscribed_group1.id,
            cls.subscribed_group2.id,
        ]
        cls.test_mail_channel = cls.env["mail.channel"].create(
            {
                "name": "Mail channel test",
                "group_ids": [(6, 0, subscribed_group_ids)],
            }
        )
        cls.test_mail_channel._subscribe_users_automatically()

    def test_unsubscribe_users(self):
        user_form_view_xid = "base_user_role.view_res_users_form_inherit"
        self.assertIn(
            self.test_user_1.partner_id, self.test_mail_channel.channel_partner_ids
        )

        # Removing self.subscribed_role1 through the form view,
        # triggering the `unsubscribe_from_mail_channel` onchange method
        with Form(self.test_user_1, user_form_view_xid) as f:
            records = f.role_line_ids._records
            f.role_line_ids.remove(
                self.find_role_rec_index(self.subscribed_role1, records)
            )

        self.assertIn(
            self.test_user_1.partner_id, self.test_mail_channel.channel_partner_ids
        )

        # Removing self.subscribed_role2 through the form view,
        # triggering the `unsubscribe_from_mail_channel` onchange method
        with Form(self.test_user_1, user_form_view_xid) as f:
            records = f.role_line_ids._records
            f.role_line_ids.remove(
                self.find_role_rec_index(self.subscribed_role2, records)
            )

        self.assertNotIn(
            self.test_user_1.partner_id, self.test_mail_channel.channel_partner_ids
        )
