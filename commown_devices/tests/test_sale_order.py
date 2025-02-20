from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from odoo.addons.product_rental.tests.common import MockedEmptySessionMixin

from .common import add_attributes_to_product, create_config


class SaleOrderTC(MockedEmptySessionMixin, SavepointCase):
    "Test class for sale order methods"

    def create_sale_order(self, product):
        oline = {
            "name": product.name,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": 1,
            "price_unit": product.list_price,
        }

        partner = self.env.ref("base.res_partner_address_1")
        return self.env["sale.order"].create(
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
        pt = self.env["product.template"].create(
            {"name": "fp", "type": "product", "tracking": "serial"}
        )
        so = self.create_sale_order(pt.product_variant_id)

        partner = so.partner_id
        partner2 = partner.copy({"name": "Test"})

        # Prerequisites: partners belong to same company and have default stock location
        customer_loc = self.env.ref("stock.stock_location_customers")
        self.assertEqual(partner.commercial_partner_id, partner2.commercial_partner_id)
        self.assertEqual(partner.property_stock_customer, customer_loc)
        self.assertEqual(partner2.property_stock_customer, customer_loc)

        # Start test:
        so.action_confirm()

        # Check a new customer loc was created...
        new_dest_loc = so.partner_id.property_stock_customer
        self.assertNotEqual(new_dest_loc, customer_loc)
        self.assertEqual(new_dest_loc.usage, "customer")
        # ... that belongs to the partner's company...
        self.assertEqual(new_dest_loc.partner_id, partner.commercial_partner_id)
        # ... and is used as the destination of the tracked products
        self.assertEqual(so.mapped("picking_ids.location_dest_id"), new_dest_loc)

        # Check another sale to the same company does not create another location
        # when confirmed, but the sale partner gets the same customer location:
        so2 = so.copy({"partner_shipping_id": partner2.id})
        so2.action_confirm()
        self.assertEqual(so2.partner_id.property_stock_customer, new_dest_loc)

    def test_action_add_services_storable_products(self):
        color_attr = self.env.ref("product.product_attribute_2")
        color1 = color_attr.value_ids[1]

        def colored1(pt):
            return pt.mapped("product_variant_ids").filtered(
                lambda pv: color1 in pv.attribute_value_ids.ensure_one()
            )

        ct = self.env["contract.template"].create(
            {"name": "Services for a sale", "stock_ownership": "customer"}
        )
        service = self.env["product.template"].create(
            {"name": "FP", "type": "service", "property_contract_template_id": ct.id}
        )
        storable = self.env["product.template"].create(
            {"name": "FP", "type": "product", "tracking": "serial"}
        )

        add_attributes_to_product(service, color_attr, color_attr.value_ids)
        add_attributes_to_product(storable, color_attr, color_attr.value_ids)
        service.create_variant_ids()
        storable.create_variant_ids()

        for color in color_attr.value_ids:
            create_config(service, "primary", storable, colored1(storable), color1)

        so = self.create_sale_order(colored1(service))
        so_lines = so.order_line

        so.action_add_services_storable_products()
        new_so_line = so.order_line - so_lines
        self.assertEqual(new_so_line.product_id.product_tmpl_id, storable)
        self.assertIn(color1, new_so_line.product_id.attribute_value_ids)

        so.action_confirm()
        with self.assertRaises(UserError):
            so.action_add_services_storable_products()

        # Also check the picking creation on order confirmation was deactivated
        self.assertFalse(so.picking_ids)
