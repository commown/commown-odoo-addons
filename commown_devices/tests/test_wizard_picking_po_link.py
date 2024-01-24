from datetime import date, datetime

from .common import DeviceAsAServiceTC


class PickingPoLinkWizardTC(DeviceAsAServiceTC):
    def setUp(self):
        super().setUp()
        supplier = self.env.ref("base.res_partner_3")
        self.previous_po_of_supplier = self.env["purchase.order"].search(
            [
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    supplier.commercial_partner_id.id,
                )
            ]
        )

        self.fp = self.env.ref("product_rental.prod_fp")
        self.pc1 = self.env.ref("product_rental.prod_pc_i5")
        self.pc2 = self.env.ref("product_rental.prod_pc_i7")

        date_po = date(2021, 1, 1)

        oline1 = self._oline(self.fp, product_qty=3, date_planned=date_po)
        oline2 = self._oline(self.pc1, product_qty=5, date_planned=date_po)
        oline3 = self._oline(self.pc2, product_qty=8, date_planned=date_po)
        self.po = self.env["purchase.order"].create(
            {
                "partner_id": supplier.id,
                "order_line": [oline1, oline2, oline3],
            }
        )

        picking_type = self.env.ref("stock.picking_type_in")
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        stock_location = self.env.ref("stock.stock_location_stock")
        date_pick = datetime(2020, 1, 1, 12, 0, 0)

        base_move_line = {"product_uom_qty": 4}
        self.picking = self.env["stock.picking"].create(
            {
                "move_type": "direct",
                "partner_id": supplier.id,
                "picking_type_id": picking_type.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
                "date": date_pick,
                "date_done": date_pick,
                "move_lines": [
                    (
                        0,
                        0,
                        dict(
                            base_move_line,
                            product_id=p.id,
                            name=p.name,
                            product_uom=p.uom_id.id,
                        ),
                    )
                    for p in [self.fp, self.pc1, self.pc2]
                ],
            }
        )

    def _filter_previous_orders(self, po_ids):
        """Filter the recordset from previously existing pos"""
        return po_ids - self.previous_po_of_supplier

    def prepare_wizard(self, related_entity, relation_field, user_choices=None):
        wizard_name = "picking.po.link.wizard"
        return self.prepare_ui(
            wizard_name, related_entity, relation_field, user_choices=user_choices
        )

    def create_wizard(self):
        return (
            self.env["picking.po.link.wizard"]
            .with_context(
                {"active_ids": [self.picking.id], "default_picking_id": self.picking.id}
            )
            .create({})
        )

    def test_default_link_lines(self):
        wizard = self.create_wizard()
        self.assertEqual(len(wizard.link_line_ids), 3)
        self.assertEqual(
            wizard.link_line_ids.mapped("move_id"), self.picking.move_lines
        )

    def test_po_id_domain(self):
        default, possibilities = self.prepare_wizard(self.picking, "picking_id")
        self.assertEqual(
            self._filter_previous_orders(possibilities["po_id"]),
            self.po,
        )
        self.picking.partner_id = False
        default, possibilities = self.prepare_wizard(self.picking, "picking_id")
        self.assertEqual(
            possibilities["po_id"],
            self.env["purchase.order"].search([]),
        )

    def test_purchase_line_id_domain(self):
        wizard = self.create_wizard()
        self.assertEqual(
            set(wizard.mapped("link_line_ids.purchase_line_id_domain")),
            {'[["order_id", "=", false]]'},
        )
        wizard.po_id = self.po.id
        wizard.link_line_ids._compute_purchase_line_id_domain()
        self.assertEqual(
            set(wizard.mapped("link_line_ids.purchase_line_id_domain")),
            {'[["order_id", "=", %s]]' % self.po.id},
        )

    def test_assign_po(self):
        # Check prerequisite
        self.assertFalse(self.picking.purchase_id)
        self.assertFalse(self.picking.origin)
        self.assertFalse(self.picking.origin)

        wizard = (
            self.env["picking.po.link.wizard"]
            .with_context(
                {"active_ids": [self.picking.id], "default_picking_id": self.picking.id}
            )
            .create({})
        )
        wizard.po_id = self.po.id
        for line_num in range(len(wizard.link_line_ids)):
            wizard.link_line_ids[line_num].purchase_line_id = self.po.order_line[
                line_num
            ]
        wizard.action_assign_po()

        # Check results
        self.assertEqual(self.picking.purchase_id, self.po)
        self.assertEqual(self.picking.origin, self.po.name)
        self.assertEqual(
            self.picking.move_lines.mapped("purchase_line_id"),
            self.po.mapped("order_line"),
        )
