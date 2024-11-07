from odoo.tests.common import SavepointCase


class FunctionalTC(SavepointCase):
    "Functional tests for product valuation mixing rental and sale locations"

    def adjust_stock(self, product, location, quantity=1):
        inventory = self.env["stock.inventory"].create(
            {
                "name": "test functionnal",
                "location_id": location.id,
                "filter": "product",
                "product_id": product.id,
            }
        )
        inventory.action_start()
        inventory.line_ids |= self.env["stock.inventory.line"].create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "product_qty": quantity,
            }
        )
        inventory.action_validate()

    def create_picking(self, picking_type, product, quantity=1, **kwargs):
        attrs = dict(
            {
                "picking_type_id": picking_type.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
            },
            **kwargs,
        )

        picking = self.env["stock.picking"].create(attrs)

        move = self.env["stock.move"].create(
            {
                "name": product.name,
                "picking_id": picking.id,
                "picking_type_id": picking.picking_type_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "date": picking.date,
                "date_expected": picking.date,
            }
        )

        picking.action_confirm()
        picking.action_assign()
        move.move_line_ids.update({"qty_done": quantity})
        picking.button_validate()

        return picking

    def get_stock_valuation_move_lines(self, pt):
        return self.env["account.move.line"].search(
            [
                ("account_id", "=", pt.categ_id.property_stock_valuation_account_id.id),
                ("product_id", "=", pt.id),
            ]
        )

    def test(self):
        ref = self.env.ref

        pt = ref("product.product_delivery_01_product_template")
        pt.property_valuation = "real_time"
        product = pt.product_variant_id

        supplier_loc = ref("stock.stock_location_suppliers")

        pick_sale_in = ref("stock.picking_type_in")
        pick_rental_in = ref("stock_account_rental.stock_picking_type_in_rental")
        pick_internal = ref("stock.picking_type_internal")

        self.adjust_stock(product, supplier_loc, 10)

        # Receive the product from supplier to the sale location:
        self.assertFalse(self.get_stock_valuation_move_lines(pt))  # pre-condition
        self.create_picking(pick_sale_in, product, location_id=supplier_loc.id)
        # ... and check 1 stock valuation line was created:
        self.assertEqual(len(self.get_stock_valuation_move_lines(pt)), 1)

        # Receive the product from supplier to the rental location:
        old_val_moves_nb = len(self.get_stock_valuation_move_lines(pt))
        self.create_picking(pick_rental_in, product, location_id=supplier_loc.id)
        # ... and check no stock valuation line was created:
        self.assertEqual(len(self.get_stock_valuation_move_lines(pt)), old_val_moves_nb)

        # Move the product from the sale to the rental area
        transfer = self.create_picking(
            pick_internal,
            product,
            location_id=pick_sale_in.default_location_dest_id.id,
            location_dest_id=pick_rental_in.default_location_dest_id.id,
        )
        moves = self.get_stock_valuation_move_lines(pt)
        self.assertEqual(sum(moves.mapped("balance")), 0.0)
