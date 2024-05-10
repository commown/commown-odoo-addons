from odoo.tests import SavepointCase


class ResUsersTC(SavepointCase):
    "Test the user methods implemented in current module"

    def test_is_authorized_to_order_b2c(self):
        portal_user = self.env.ref("base.demo_user0")

        # Check test prerequisite:
        self.assertFalse(portal_user.partner_id.commercial_partner_id.is_company)

        # Actual test:
        self.assertTrue(portal_user.is_authorized_to_order())

    def test_is_authorized_to_order_b2b(self):
        portal_user = self.env.ref("base.demo_user0")
        portal_user.partner_id.parent_id = self.env.ref("base.res_partner_1").id

        # Check unauthorized when not in the purchase group:
        self.assertFalse(portal_user.is_authorized_to_order())

        # Check authorized when in the purchase group:
        purchase_group = self.env.ref("customer_manager_base.group_customer_purchase")
        purchase_group.users |= portal_user
        self.assertTrue(portal_user.is_authorized_to_order())
