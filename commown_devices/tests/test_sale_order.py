from odoo.tests.common import SavepointCase


class SaleOrderTC(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(SaleOrderTC, cls).setUpClass()

        pt_args = {"name": "fp", "type": "product", "tracking": "serial"}
        product = cls.env["product.template"].create(pt_args).product_variant_id
        oline = {
            "name": product.name,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": 1,
            "price_unit": product.list_price,
        }

        partner = cls.env.ref("base.res_partner_address_1")
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [
                    (0, 0, oline),
                ],
            }
        )

    def test_action_confirm(self):
        partner = self.so.partner_id
        partner2 = partner.copy({"name": "Test"})

        # Prerequisites: partners belong to same company and have default stock location
        customer_loc = self.env.ref("stock.stock_location_customers")
        self.assertEqual(partner.commercial_partner_id, partner2.commercial_partner_id)
        self.assertEqual(partner.property_stock_customer, customer_loc)
        self.assertEqual(partner2.property_stock_customer, customer_loc)

        # Start test:
        self.so.action_confirm()

        # Check a new customer loc was created...
        new_dest_loc = self.so.partner_id.property_stock_customer
        self.assertNotEqual(new_dest_loc, customer_loc)
        self.assertEqual(new_dest_loc.usage, "customer")
        # ... that belongs to the partner's company...
        self.assertEqual(new_dest_loc.partner_id, partner.commercial_partner_id)
        # ... and is used as the destination of the tracked products
        self.assertEqual(self.so.mapped("picking_ids.location_dest_id"), new_dest_loc)

        # Check another sale to the same company does not create another location
        # when confirmed, but the sale partner gets the same customer location:
        so2 = self.so.copy({"partner_shipping_id": partner2.id})
        so2.action_confirm()
        self.assertEqual(so2.partner_id.property_stock_customer, new_dest_loc)
