from odoo.tests import common


class UserUnsubscribeChannelTC(common.SavepointCase):
    @classmethod
    def _create_group(cls, name):
        return cls.env["res.groups"].create({"name": name})

    @classmethod
    def _create_role(cls, name, group, user):
        # create a role from name and associated group and add the user in
        role = cls.env["res.users.role"].create(
            {
                "name": name,
                "group_id": group.id,
                "line_ids": [(0, 0, {"user_id": user.id})],
            }
        )
        return role

    @classmethod
    def _add_user_to_role(cls, user, role):
        line_id = cls.env["res.user.role.line"].create(
            {"role_id": role.id, "user_id": user.id}
        )

    @classmethod
    def _copy_user_role_to_origin(cls, user):
        roles_to_add = user.role_ids.filtered(
            lambda r: r.id not in user._origin.role_ids.mapped("id")
        )
        roles_to_remove = user._origin.role_ids.filtered(
            lambda r: r.id not in user.role_ids.mapped("id")
        )
        for role in roles_to_add:
            cls.env["res.users.role.line"].create(
                {
                    "role_id": role.id,
                    "user_id": user._origin.id,
                }
            )

        cls.env["res.users.role.line"].search(
            [
                ("user_id.id", "=", cls.test_user_1._origin.id),
            ]
        ).filtered(lambda rl: rl.role_id.id in roles_to_remove.mapped("id")).unlink()

    @classmethod
    def setUpClass(cls):
        super(UserUnsubscribeChannelTC, cls).setUpClass()

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

        role_ids = [
            cls.subscribed_role1.id,
            cls.subscribed_role2.id,
            cls.nonsubscribed_role.id,
        ]
        subscribed_group_ids = [
            cls.subscribed_group1.id,
            cls.subscribed_group2.id,
        ]
        cls.test_mail_channel = cls.env["mail.channel"].create(
            {
                "name": "Mail channel test",
                "public": "private",
                "group_ids": [(6, 0, subscribed_group_ids)],
            }
        )
        cls.test_mail_channel._subscribe_users()

    def test_unsubscribe_users(self):

        self.assertIn(
            self.test_user_1.partner_id.id,
            self.test_mail_channel.channel_last_seen_partner_ids.mapped(
                "partner_id.id"
            ),
        )
        # Emulate _origin we get from onchange call
        self.test_user_1._origin = self.test_user_1.copy({"login": "test2"})
        self._copy_user_role_to_origin(self.test_user_1)

        self.test_user_1.unsubscribe_from_mail_channel()
        self.assertIn(
            self.test_user_1.partner_id.id,
            self.test_mail_channel.channel_last_seen_partner_ids.mapped(
                "partner_id.id"
            ),
        )

        self._copy_user_role_to_origin(self.test_user_1)
        self.env["res.users.role.line"].search(
            [
                ("role_id.id", "=", self.subscribed_role1.id),
                ("user_id.id", "=", self.test_user_1.id),
            ]
        ).unlink()

        self.test_user_1.unsubscribe_from_mail_channel()
        self.assertIn(
            self.test_user_1.partner_id.id,
            self.test_mail_channel.channel_last_seen_partner_ids.mapped(
                "partner_id.id"
            ),
        )

        self._copy_user_role_to_origin(self.test_user_1)
        self.env["res.users.role.line"].search(
            [
                ("role_id.id", "=", self.subscribed_role2.id),
                ("user_id.id", "=", self.test_user_1.id),
            ]
        ).unlink()

        self.test_user_1.unsubscribe_from_mail_channel()

        self.assertNotIn(
            self.test_user_1.partner_id.id,
            self.test_mail_channel.channel_last_seen_partner_ids.mapped(
                "partner_id.id"
            ),
        )
