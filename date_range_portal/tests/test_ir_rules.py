from odoo.tests import SavepointCase


class PortalDateRangeTypeIRRulesTC(SavepointCase):
    def setUp(self):
        super().setUp()

        self.portal_user = self.env.ref("base.demo_user0")
        self.assertTrue(self.portal_user.has_group("base.group_portal"))

    def test_read(self):
        results = (
            self.env["date.range.type"]
            .sudo(self.portal_user)
            .search_read([], fields=["name"])
        )
        self.assertFalse(results)
