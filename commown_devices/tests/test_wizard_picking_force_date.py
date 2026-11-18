from datetime import datetime, timedelta

from odoo.exceptions import UserError

from ..models.common import do_new_transfer, internal_picking
from .common import BaseLotTC
from .test_common import create_stock_location


class WizardForcePickingDateTC(BaseLotTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("stock.picking_type_internal").reservation_method = "manual"

        cls.loc_a = create_stock_location(cls, "Location A")
        cls.loc_b = create_stock_location(cls, "Location B")
        cls.loc_c = create_stock_location(cls, "Location C")

        cls.quant.location_id = cls.loc_a
        ## Created pickings order (broken on purpose) :
        # 2: 2026-10-31: Loc. B -> Loc. C
        # 1: 2026-11-05: Loc. A -> Loc. B
        # 3: 2026-11-15: Loc. C -> Loc. A

        cls.base_date = datetime(year=2026, month=11, day=5)
        cls.picking_1 = cls._create_and_validate_picking(
            cls.lot, cls.loc_a, cls.loc_b, cls.base_date
        )

        cls.picking_2 = cls._create_and_validate_picking(
            cls.lot, cls.loc_b, cls.loc_c, cls.base_date - timedelta(days=5)
        )

        cls.picking_3 = cls._create_and_validate_picking(
            cls.lot, cls.loc_c, cls.loc_a, cls.base_date + timedelta(days=10)
        )

    @classmethod
    def _create_and_validate_picking(cls, lot, orig, dest, date):
        picking = internal_picking(
            lot, {}, cls.env["stock.location"], orig, dest, False, date=date
        ).picking_id
        do_new_transfer(picking, date)

        return picking

    def _generate_force_picking_date_wiz(self, picking):
        self.wizard = (
            self.env["force.picking.date.wizard"]
            .with_context(active_id=picking.id)
            .create({})
        )

    def _set_date_on_wiz_line(self, picking, new_date):
        wiz_line = self.wizard.wizard_line_ids.filtered(
            lambda l: l.picking_id == picking
        ).ensure_one()

        wiz_line.new_date = new_date

    def _set_to_delete_on_wiz_line(self, picking, to_delete):
        wiz_line = self.wizard.wizard_line_ids.filtered(
            lambda l: l.picking_id == picking
        )

        wiz_line.to_delete = to_delete

    def test_wizard_ok_same_destination(self):
        # Using the wizard to fix the tracked lot history
        self._generate_force_picking_date_wiz(self.picking_2)
        self.assertFalse(self.wizard.is_history_coherent)

        new_date = self.base_date + timedelta(days=5)
        self._set_date_on_wiz_line(self.picking_2, new_date)
        self.assertTrue(self.wizard.is_history_coherent)

        self.wizard.execute()

        self.picking_2.invalidate_recordset()
        self.assertEqual(self.picking_2.scheduled_date, new_date)
        self.assertEqual(self.picking_2.date_done, new_date)

        pick_moves = self.picking_2.move_ids
        self.assertEqual(pick_moves.date, new_date)
        self.assertEqual(pick_moves.move_line_ids.date, new_date)

    def test_wizard_ok_new_destination(self):
        # Same as above, but the modification leads to a new destination location
        self._generate_force_picking_date_wiz(self.picking_1)
        self.assertFalse(self.wizard.is_history_coherent)

        # Putting picking 3 behind picking 1, so the new order is B -> C -> A -> B
        # with B as the new destination.
        new_date = self.base_date - timedelta(days=1)
        self._set_date_on_wiz_line(self.picking_3, new_date)
        self.assertTrue(self.wizard.is_history_coherent)

        self.wizard.execute()
        self.picking_1.invalidate_recordset()
        self.assertEqual(self.picking_3.date_done, new_date)

        lot_quant = self.env["stock.quant"].search(
            [
                ("lot_id", "=", self.lot.id),
                ("quantity", "=", 1.0),
            ]
        )
        self.assertEqual(lot_quant.location_id, self.loc_b)

    def test_wizard_ok_deleted_picking(self):
        "Deleting a picking should remove it and its move lines, while maintaing a good history"
        self._generate_force_picking_date_wiz(self.picking_1)
        self.assertFalse(self.wizard.is_history_coherent)

        # In this exemple, we will delete Picking 1,
        # with the final intended track being: B -> C -> A
        move_p1 = self.picking_1.move_ids

        self._set_to_delete_on_wiz_line(self.picking_1, True)
        self.assertTrue(self.wizard.is_history_coherent)

        self.wizard.execute()

        self.assertFalse(self.picking_1.exists())
        self.assertFalse(move_p1.exists())

    def test_wizard_ko_incoherent_history(self):
        # Trying to confirm changes for an incoherent history should raise an error
        self._generate_force_picking_date_wiz(self.picking_2)
        self.assertFalse(self.wizard.is_history_coherent)

        with self.assertRaises(UserError) as exc:
            self.wizard.execute()

        self.assertIn("device history is incoherent", exc.exception.args[0])

    def test_wizard_ko_reserved_lot_at_creation(self):
        "Device history modification is forbidden if the device is currently reserved."
        picking = internal_picking(
            self.lot, {}, self.env["stock.location"], self.loc_a, self.loc_b, False
        ).picking_id

        with self.assertRaises(UserError) as exc:
            self._generate_force_picking_date_wiz(self.picking_2)

        self.assertIn(f"following picking(s): {picking.name}", exc.exception.args[0])

    def test_wizard_ko_reserved_lot_at_execute(self):
        "If a picking is created after opening a wizard, forbid executing the wizard"
        self._generate_force_picking_date_wiz(self.picking_2)

        new_date = self.base_date + timedelta(days=5)
        self._set_date_on_wiz_line(self.picking_2, new_date)
        self.assertTrue(self.wizard.is_history_coherent)

        picking = internal_picking(
            self.lot, {}, self.env["stock.location"], self.loc_a, self.loc_b, False
        ).picking_id

        with self.assertRaises(UserError) as exc:
            self.wizard.execute()

        self.assertIn(f"following picking(s): {picking.name}", exc.exception.args[0])
