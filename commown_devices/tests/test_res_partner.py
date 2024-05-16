from odoo.tests.common import HttpCase, at_install, post_install

from ..models.common import internal_picking


@at_install(False)
@post_install(True)
class ResPartnerLocationTC(HttpCase):
    "Class related to partner methods implemented in present module"

    def test_customer_location_individual(self):
        employee = self.env.ref("base.user_demo")
        individual = self.env.ref("base.partner_demo_portal")
        loc_customer = self.env.ref("stock.stock_location_customers")
        assert (
            individual.property_stock_customer == loc_customer
        ), "test prerequisite failed"

        location = individual.sudo(employee.id).get_or_create_customer_location()
        self.assertNotEqual(location, loc_customer)
        self.assertEqual(location.usage, "internal")
        self.assertIn(individual.name, location.name)
        self.assertEqual(location, individual.get_or_create_customer_location())

    def test_customer_location_pro(self):
        company = self.env.ref("base.res_partner_2")
        pro1, pro2 = self.env["res.partner"].search(
            [
                ("parent_id", "=", company.id),
                ("type", "=", "contact"),
            ],
            limit=2,
        )

        location1 = pro1.get_or_create_customer_location()
        location2 = pro2.get_or_create_customer_location()
        location3 = company.get_or_create_customer_location()

        self.assertEqual(location3, location1)
        self.assertEqual(location3, location2)

        self.assertEqual(location1.partner_id, company)
        self.assertEqual(location1.usage, "internal")

    def test_customer_location_local_employee(self):
        company = self.env["res.partner"].browse(1)
        pro = self.env["res.partner"].search(
            [
                ("parent_id", "=", company.id),
                ("type", "=", "contact"),
            ],
            limit=1,
        )

        self.assertNotEqual(
            pro.get_or_create_customer_location(),
            company.get_or_create_customer_location(),
        )

    def _new_dev(self, name, product, location):
        lot = self.env["stock.production.lot"].create(
            {"name": name, "product_id": product.id}
        )

        inventory = self.env["stock.inventory"].create(
            {
                "name": "test stock %s" % lot.name,
                "location_id": location.id,
                "filter": "lot",
                "lot_id": lot.id,
            }
        )
        inventory.action_start()
        inventory.line_ids |= self.env["stock.inventory.line"].create(
            {
                "product_id": lot.product_id.id,
                "location_id": location.id,
                "prod_lot_id": lot.id,
                "product_qty": 1,
            }
        )
        inventory.action_validate()
        return lot

    def _send(self, lot, orig, dest):
        return internal_picking(lot, {}, None, orig, dest, False, do_transfer=True)

    def test_merge_partner_merge_locations(self):
        new_dev_loc = self.env["stock.location"].create(
            {
                "name": "New devices",
                "usage": "internal",
                "partner_id": 1,
                "location_id": self.env.ref(
                    "commown_devices.stock_location_new_devices"
                ).id,
            }
        )
        customer_loc = self.env.ref("stock.stock_location_customers")

        p1 = self.env.ref("base.partner_demo_portal")
        loc_p1 = p1.get_or_create_customer_location()

        p2 = p1.copy({"email": p1.email.capitalize()})
        loc_p2 = p2.get_or_create_customer_location()

        pt = self.env["product.template"].create(
            {"name": "My test product", "type": "product", "tracking": "serial"}
        )
        lot1 = self._new_dev("lot1", pt.product_variant_id, new_dev_loc)
        lot2 = self._new_dev("lot2", pt.product_variant_id, new_dev_loc)

        picking_1 = self._send(lot1, new_dev_loc, loc_p1)
        picking_2 = self._send(lot2, new_dev_loc, loc_p2)

        self.assertEqual(lot1.current_location(customer_loc), loc_p1)
        self.assertEqual(lot2.current_location(customer_loc), loc_p2)

        wiz = self.env["base.partner.merge.automatic.wizard"].create(
            {"partner_ids": [(6, 0, [p1.id, p2.id])], "dst_partner_id": p2.id}
        )
        wiz.action_merge()

        self.assertFalse(p1.exists())
        self.assertTrue(p2.exists())

        self.assertTrue(loc_p1.exists())
        self.assertFalse(loc_p2.exists())

        self.assertEqual(picking_1.location_dest_id, loc_p1)
        self.assertEqual(picking_2.location_dest_id, loc_p1)

        self.assertEqual(lot1.current_location(customer_loc), loc_p1)
        self.assertEqual(lot2.current_location(customer_loc), loc_p1)
