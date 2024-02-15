from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.commown_devices.tests.common import DeviceAsAServiceTC

from .common import RentedQuantityTC


class ResPartnerTC(RentedQuantityTC):
    "Test this module's partner methods"

    def test_rented_quantity(self):
        "Rented quantity must account for contracts of the upper level company"
        same_company_partner = self.so.partner_id.copy({"name": "Darmanin Autrou"})
        same_company_partner.action_create_intermediate_company()
        rented_quantity = same_company_partner.rented_quantity

        self.assertEqual(rented_quantity(product_template=self.fp_premium), 1)
        self.assertEqual(rented_quantity(product_template=self.fp2), 1)
        self.assertEqual(rented_quantity(product_category=self.cat_fp), 2)
        self.assertEqual(rented_quantity(product_category=self.cat_fp_premium), 1)

    def test_action_create_intermediate_company_error(self):
        comp = self.env["res.partner"].create({"name": "company", "is_company": True})
        c1 = self.env["res.partner"].create({"name": "c1"})
        c2 = self.env["res.partner"].create({"name": "c2", "parent_id": comp.id})
        c3 = self.env["res.partner"].create({"name": "c3"})

        with self.assertRaises(UserError) as err:
            (c1 | c2 | c3).action_create_intermediate_company()

        self.assertEqual(
            err.exception.name,
            "Partners not suitable for intermediate company creation:"
            "\n- c1 (id %d)\n- c3 (id %d)" % (c1.id, c3.id),
        )


@tagged("post_install", "-at_install")
class ResPartnerWithContractStockTC(DeviceAsAServiceTC):
    def test_action_create_intermediate_company_ok(self):
        # Make contract a B2B one
        comp = self.env["res.partner"].create({"name": "Company", "is_company": True})
        p1 = self.env["res.partner"].create({"name": "p1", "parent_id": comp.id})
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        contract.partner_id = p1.id

        # Send a device in the context of this contract
        lot1 = self.adjust_stock(serial="my-fp3-1")
        picking1 = contract.send_devices(lot1, {}, date="2024-01-01", do_transfer=True)
        loc_init = p1.get_customer_location()

        # Create another partner in the base company
        p2 = self.env["res.partner"].create({"name": "p2", "parent_id": comp.id})
        so2 = self.so.copy({"partner_id": p2.id})
        so2.action_confirm()
        contract2 = self.env["contract.contract"].of_sale(so2)[0]
        lot2 = self.adjust_stock(serial="my-fp3-2")
        picking2 = contract2.send_devices(lot2, {}, date="2023-12-01", do_transfer=True)

        # ... and create an intermediate company for partner 1
        p1.action_create_intermediate_company()

        # Check that the partner 1 was moved to the new company
        self.assertEqual(p1.parent_id.parent_id, comp)
        self.assertTrue(p1.parent_id.is_company)
        self.assertEqual(p1.parent_id.name, "p1 (indep. - Company)")

        # ... but not partner 2, whose location is still the initial one
        self.assertEqual(p2.parent_id, comp)
        self.assertEqual(p2.get_customer_location(), loc_init)

        # ... and check that the contract stock has moved to the new
        # partner 1's location
        loc_new = p1.get_customer_location()
        self.assertTrue(loc_init != loc_new)
        self.assertEqual(loc_new.partner_id, p1.parent_id)
        self.assertEqual(picking1.location_dest_id, loc_new)
        quant1 = self.env["stock.quant"].search(
            [("lot_id", "=", lot1.id), ("quantity", ">", 0)],
        )
        self.assertEqual(quant1.location_id, loc_new)

        # ... but that contract 2 stock is still in the initial location
        self.assertEqual(picking2.location_dest_id, loc_init)
        quant2 = self.env["stock.quant"].search(
            [("lot_id", "=", lot2.id), ("quantity", ">", 0)],
        )
        self.assertEqual(quant2.location_id, loc_init)

        # Check that lots are still associated with the rigth contract
        self.assertEqual(contract.lot_ids, lot1)
        self.assertEqual(contract2.lot_ids, lot2)
        self.assertEqual(quant2.location_id, loc_init)
