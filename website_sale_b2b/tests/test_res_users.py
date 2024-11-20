from odoo.tests import SavepointCase


class ResUsersTC(SavepointCase):
    "Test the user methods implemented in current module"

    def setUp(self):
        super().setUp()
        self.user = self.env.ref("base.demo_user0")
        self.assertFalse(self.user.partner_id.commercial_partner_id.is_company)

    def set_in_purchase_group(self, user, true_false):
        purchase_group = self.env.ref("customer_manager_base.group_customer_purchase")
        if bool(true_false) is True:
            user.groups_id |= purchase_group
        else:
            user.groups_id -= purchase_group

    def test_is_authorized_to_order_b2c(self):
        self.set_in_purchase_group(self.user, False)
        self.assertTrue(self.user.is_authorized_to_order())

    def test_is_authorized_to_order_b2b(self):
        self.user.partner_id.parent_id = self.env.ref("base.res_partner_1").id

        # Check unauthorized when not in the purchase group:
        self.set_in_purchase_group(self.user, False)
        self.assertFalse(self.user.is_authorized_to_order())

        # Check authorized when in the purchase group:
        self.set_in_purchase_group(self.user, True)
        self.assertTrue(self.user.is_authorized_to_order())
