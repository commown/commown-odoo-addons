from odoo.tests.common import HttpCase, at_install, post_install


@at_install(False)
@post_install(True)
class ResPartnerLocationTC(HttpCase):

    def test_set_customer_location_individual(self):
        individual = self.env.ref("portal.demo_user0_res_partner")
        loc_customer = self.env.ref('stock.stock_location_customers')
        assert individual.property_stock_customer == loc_customer, (
            'test prerequisite failed')

        location = individual.set_customer_location()
        self.assertNotEqual(location, loc_customer)
        self.assertIn(individual.name, location.name)
        self.assertEqual(location, individual.set_customer_location())

    def test_set_customer_location_pro(self):
        company = self.env.ref("base.res_partner_2")
        pro1, pro2 = self.env["res.partner"].search([
            ("parent_id", "=", company.id)])[0:2]

        location1 = pro1.set_customer_location()
        location2 = pro2.set_customer_location()
        location3 = company.set_customer_location()

        self.assertEqual(location3, location1)
        self.assertEqual(location3, location2)
