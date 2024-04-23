from odoo.exceptions import AccessError, UserError
from odoo.tests.common import SavepointCase


class CustomerGroupWizardTC(SavepointCase):
    def get_wizard(self, partner):
        wizard = self.env["customer_manager_base.customer_group_wizard"].create(
            {"partner_id": partner.id}
        )
        wizard._compute_in_group()
        return wizard

    def test_partner_non_portal(self):
        partner = self.env.ref("base.partner_demo")
        with self.assertRaises(UserError) as err:
            self.get_wizard(partner)
        self.assertEqual(err.exception.name, "Partner has no portal access!")

    def test_need_group_sale_manager(self):
        partner = self.env.ref("base.partner_demo_portal")
        wizard = self.get_wizard(partner)
        with self.assertRaises(AccessError) as err:
            wizard.execute()
        self.assertEqual(
            err.exception.name,
            "You are not allowed to execute this operation",
        )

    def test_partner_ok(self):
        partner = self.env.ref("base.partner_demo_portal")
        user = partner.user_ids

        def mod_ref(name):
            return self.env.ref("customer_manager_base.%s" % name)

        mod_ref("group_customer_accounting").users |= user

        wizard = self.get_wizard(partner)

        self.assertTrue(wizard.in_group_accounting)
        self.assertFalse(wizard.in_group_purchase)
        self.assertFalse(wizard.in_group_it_support)
        self.assertFalse(wizard.in_group_contract_manager)

        wizard.in_group_contract_manager = True
        self.env.ref("sales_team.group_sale_manager").users |= self.env.user
        wizard.execute()

        self.assertIn(mod_ref("group_customer_contract_manager").users, user)
        self.assertNotIn(mod_ref("group_customer_purchase").users, user)
        self.assertNotIn(mod_ref("group_customer_it_support").users, user)
