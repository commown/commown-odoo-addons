from datetime import datetime, timedelta

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

    def test_wizard_ok(self):
        # Using the wizard to fix the tracked lot history
        self._generate_force_picking_date_wiz(self.picking_2)

        new_date = self.base_date + timedelta(days=5)
        self._set_date_on_wiz_line(self.picking_2, new_date)
        self.wizard.execute()

        self.picking_2.invalidate_recordset()
        self.assertEqual(self.picking_2.scheduled_date, new_date)
        self.assertEqual(self.picking_2.date_done, new_date)

        pick_moves = self.picking_2.move_ids
        self.assertEqual(pick_moves.date, new_date)
        self.assertEqual(pick_moves.move_line_ids.date, new_date)
