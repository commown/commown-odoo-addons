from odoo.tests.common import HttpCase, at_install, post_install


@at_install(False)
@post_install(True)
class ResPartnerLocationTC(HttpCase):

    def test_customer_location_individual(self):
        employee = self.env.ref("base.user_demo")
        individual = self.env.ref("base.partner_demo_portal")
        loc_customer = self.env.ref('stock.stock_location_customers')
        assert individual.property_stock_customer == loc_customer, (
            'test prerequisite failed')

        location = individual.sudo(
            employee.id).get_or_create_customer_location()
        self.assertNotEqual(location, loc_customer)
        self.assertIn(individual.name, location.name)
        self.assertEqual(location, individual.get_or_create_customer_location())

    def test_customer_location_pro(self):
        company = self.env.ref("base.res_partner_2")
        pro1, pro2 = self.env["res.partner"].search([
            ("parent_id", "=", company.id),
            ("type", "=", "contact"),
        ], limit=2)

        location1 = pro1.get_or_create_customer_location()
        location2 = pro2.get_or_create_customer_location()
        location3 = company.get_or_create_customer_location()

        self.assertEqual(location3, location1)
        self.assertEqual(location3, location2)

        self.assertEqual(location1.partner_id, company)

    def test_customer_location_local_employee(self):
        company = self.env["res.partner"].browse(1)
        pro = self.env["res.partner"].search([
            ("parent_id", "=", company.id),
            ("type", "=", "contact"),
        ], limit=1)

        self.assertNotEqual(pro.get_or_create_customer_location(),
                            company.get_or_create_customer_location())
