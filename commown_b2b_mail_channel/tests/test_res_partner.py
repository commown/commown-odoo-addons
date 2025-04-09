from datetime import date

from odoo.tests.common import SavepointCase


class ResPartnerTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.partner"].create(
            {"name": "Company", "company_type": "company"}
        )

        user1 = self.env["res.users"].create({"name": "u1", "login": "u1"})
        user2 = self.env["res.users"].create({"name": "u2", "login": "u2"})

        self.part1 = user1.partner_id
        self.part2 = user2.partner_id

        self.user_support = self.env["res.users"].create(
            {"name": "Test support", "login": "login"}
        )

        support_role = self.env.ref("commown_user_roles.support")

        self.env["res.users.role.line"].create(
            {"user_id": self.user_support.id, "role_id": support_role.id}
        )
        support_role.update_users()

        self.contract = self.env["contract.contract"].create(
            {
                "name": "Test contract",
                "partner_id": self.part1.id,
                "date_start": "2030-01-01",
            }
        )

    def test_support_channel_creation_on_contract_start(self):
        self.part1.parent_id = self.company
        self.part2.parent_id = self.company
        self.assertFalse(self.company.mail_channel_id)

        self.contract.date_start = date.today()

        company_chan = self.company.mail_channel_id
        expected_groups = self.env["res.groups"]
        for name in ["support", "commercial", "admin"]:
            expected_groups |= self.env.ref("commown_user_roles.%s" % name).group_id

        self.assertEqual(company_chan.name, "Support of company %s" % self.company.name)
        self.assertEqual(
            company_chan.channel_partner_ids,
            self.part1 + self.part2 + self.user_support.partner_id,
        )
        self.assertEqual(company_chan.group_ids, expected_groups)

    def test_disable_automatic_subscription(self):
        self.company.disable_channel_subscription = True
        self.part1.parent_id = self.company
        self.company.create_mail_channel()
        mail_channel = self.company.mail_channel_id
        self.assertTrue(mail_channel)

        channel_partners = mail_channel.channel_partner_ids
        self.assertNotIn(self.part1, channel_partners)
        self.assertIn(self.user_support.partner_id, channel_partners)

        self.company.disable_channel_subscription = False
        self.part2.parent_id = self.company

        channel_partners = mail_channel.channel_partner_ids
        self.assertNotIn(self.part1, channel_partners)
        self.assertIn(self.part2, channel_partners)

    def test_partner_is_added_when_parent_has_channel(self):
        self.company.create_mail_channel()
        mail_channel = self.company.mail_channel_id
        self.assertTrue(mail_channel)

        self.part1.parent_id = self.company
        self.assertIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )

        self.part1.parent_id = False
        self.assertNotIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )

    def test_channel_creation_on_active_contract_join_company(self):
        """Test if channel is created when a partner with an active contract join
        company"""
        self.part2.parent_id = self.company
        self.assertFalse(self.company.mail_channel_id)

        self.contract.date_start = date.today()
        self.part1.parent_id = self.company
        self.assertTrue(self.company.mail_channel_id)

    def test_set_support_channel_name(self):
        self.company.create_mail_channel()
        self.assertEqual(
            self.company.mail_channel_id.name,
            "Support of company %s" % self.company.name,
        )

        new_name = "New name"

        self.company.name = new_name
        self.assertEqual(
            self.company.mail_channel_id.name,
            "Support of company %s" % new_name,
        )

    def test_partner_are_unsubscribed_when_company_is_changed(self):
        company_2 = self.company.copy()

        self.part1.parent_id = self.company
        self.part2.parent_id = company_2

        self.company.create_mail_channel()
        mail_channel = self.company.mail_channel_id

        self.assertIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )
        self.assertNotIn(
            self.part2,
            mail_channel.channel_partner_ids,
        )

        mail_channel.partner_company = company_2
        self.assertEqual(mail_channel.partner_company, mail_channel.partner_companies)
        self.assertIn(
            self.part2,
            mail_channel.channel_partner_ids,
        )
        self.assertNotIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )

    def test_only_concerned_partner_are_unubscribed_on_parent_change(self):
        self.part1.parent_id = self.company
        self.part2.parent_id = self.company

        self.company.create_mail_channel()
        mail_channel = self.company.mail_channel_id

        self.assertIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )
        self.assertIn(
            self.part2,
            mail_channel.channel_partner_ids,
        )

        self.part1.parent_id = False
        self.assertNotIn(
            self.part1,
            mail_channel.channel_partner_ids,
        )
        self.assertIn(
            self.part2,
            mail_channel.channel_partner_ids,
        )

    def test_access_granted_on_user_creation(self):
        self.company.create_mail_channel()

        partner = self.env["res.partner"].create(
            {"name": "test part", "email": "test@part.org"}
        )
        partner.parent_id = self.company

        self.assertNotIn(
            partner,
            self.company.mail_channel_id.channel_partner_ids,
        )

        user = self.env["res.users"]._create_user_from_template(
            {
                "email": partner.email,
                "login": partner.email,
                "partner_id": partner.id,
            }
        )

        self.assertIn(
            partner,
            self.company.mail_channel_id.channel_partner_ids,
        )

        user.unlink()
        self.assertNotIn(
            partner,
            self.company.mail_channel_id.channel_partner_ids,
        )
