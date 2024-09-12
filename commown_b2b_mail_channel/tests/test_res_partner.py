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
            {"name": "Test contract", "partner_id": self.part1.id}
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

        self.assertEqual(company_chan.name, "Support %s" % self.company.name)
        self.assertEqual(
            company_chan.channel_last_seen_partner_ids.mapped("partner_id"),
            self.part1 + self.part2 + self.user_support.partner_id,
        )
        self.assertEqual(company_chan.group_ids, expected_groups)
