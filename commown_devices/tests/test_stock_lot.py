from .common import BaseLotTC


class StockProductionLotTC(BaseLotTC):
    def test_current_location_ok(self):
        to_check_loc = self.env.ref("commown_devices.stock_location_devices_to_check")

        self.assertTrue(self.quant.quantity)  # Test prerequisite
        self.assertFalse(self.quant.reserved_quantity)  # Test prerequisite

        self.assertEqual(
            self.lot.current_location(),
            self.location_internal_available,
        )

        self.assertEqual(
            self.lot.current_location(self.location_available_for_rent),
            self.location_internal_available,
        )

        self.assertFalse(
            self.lot.current_location(to_check_loc),
            self.location_internal_available,
        )

        self.quant.reserved_quantity = 1
        self.assertEqual(
            self.lot.current_location(),
            self.location_internal_available,
        )

    def test_current_location_raises(self):
        to_check_loc = self.env.ref("commown_devices.stock_location_devices_to_check")
        for_rent_loc = self.location_available_for_rent

        with self.assertRaises(Warning) as err:
            self.lot.current_location(to_check_loc, raise_if_not_found=True)
        self.assertEqual(
            "Lot %s not found in available stock" % self.lot.name,
            err.exception.args[0],
        )

        self.quant.quantity = 0
        with self.assertRaises(Warning) as err:
            self.lot.current_location(raise_if_not_found=True)
        self.assertEqual(
            "Lot %s not found in available stock" % self.lot.name,
            err.exception.args[0],
        )

        self.quant.quantity = 1
        self.quant.reserved_quantity = 1
        with self.assertRaises(Warning) as err:
            self.lot.current_location(for_rent_loc, raise_if_reserved=True)
        self.assertEqual(
            "Lot %s is already reserved" % self.lot.name,
            err.exception.args[0],
        )

        # Not found error has priority over reserved
        with self.assertRaises(Warning) as err:
            self.lot.current_location(
                to_check_loc, raise_if_not_found=True, raise_if_reserved=True
            )
        self.assertEqual(
            "Lot %s not found in available stock" % self.lot.name,
            err.exception.args[0],
        )
