from .common import BaseLotTC


class StockProductionLotTC(BaseLotTC):
    def test_current_location(self):
        self.assertEqual(
            self.lot.current_location(self.location_available_for_rent),
            self.location_internal_available,
        )
        self.quant.quantity = 0
        with self.assertRaises(Warning) as err1:
            self.lot.current_location(self.location_available_for_rent)
        self.assertEqual(
            "Lot %s not found in available stock" % self.lot.name,
            err1.exception.args[0],
        )
        self.quant.quantity = 1
        self.quant.reserved_quantity = 1
        with self.assertRaises(Warning) as err2:
            self.lot.current_location(self.location_available_for_rent)
        self.assertEqual(
            "Lot %s is already reserved" % self.lot.name,
            err2.exception.args[0],
        )
