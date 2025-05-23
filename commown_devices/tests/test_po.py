from odoo.tests.common import TransactionCase


class PurchaseOrderTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.po = cls.env.ref("purchase.purchase_order_1")
        cls.product = cls.po.order_line[0].product_id
        cls.po.order_line[1:].unlink()

        assert cls.product.type == "product"

        cls.product.tracking = "lot"

    def get_grade(self, ref):
        return self.env.ref("commown_grade.grade_%s" % ref)

    def _deliver_po(self):
        self.po.button_confirm()

        picking = self.po.picking_ids
        picking.action_assign()

        picking.move_line_ids.qty_done = picking.move_line_ids.product_qty
        picking.move_line_ids.lot_name = "Lot 1"
        picking.button_validate()

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
