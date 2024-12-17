from odoo.tests.common import SavepointCase


class PurchaseOrderTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.po = self.env.ref("purchase.purchase_order_1")
        self.product = self.po.order_line[0].product_id
        self.po.order_line[1:].unlink()

        assert self.product.type == "product"

        self.product.tracking = "lot"

    def get_grade(self, ref):
        return self.env.ref("commown_grade.grade_%s" % ref)

    def _deliver_po(self):
        self.po.button_confirm()

        picking = self.po.picking_ids
        picking.action_assign()

        picking.move_line_ids.qty_done = picking.move_line_ids.product_qty
        picking.move_line_ids.lot_name = "Lot 1"
        picking.action_done()

    def test_default(self):
        self.assertEqual(
            self.env["purchase.order"].default_get(["default_product_grade"]),
            {"default_product_grade": self.get_grade("A0").id},
        )

    def test_grade_set(self):
        self.po.default_product_grade = self.get_grade("A1")

        self._deliver_po()
        lot = self.po.picking_ids.move_line_ids.lot_id

        self.assertEqual(lot.grade_id.name, "Grade A1")
        self.assertEqual(len(lot.grade_history_line_ids), 1)

    def test_grade_empty(self):
        self.po.default_product_grade = False

        self._deliver_po()
        lot = self.po.picking_ids.move_line_ids.lot_id

        self.assertFalse(lot.grade_id)
        self.assertFalse(lot.grade_history_line_ids)
