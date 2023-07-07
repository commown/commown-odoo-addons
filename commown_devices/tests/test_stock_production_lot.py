from odoo.tests.common import SavepointCase


class StockProductionLotTC(SavepointCase):
    def setUp(self, *args, **kwargs):
        super(StockProductionLotTC, self).setUp(*args, **kwargs)

        self.product_tmpl = self.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
            }
        )
        self.product = self.product_tmpl.product_variant_id
        self.lot = self.env["stock.production.lot"].create(
            {
                "name": "test-lot",
                "product_id": self.product.id,
            }
        )
        self.location_available_for_rent = self.env.ref(
            "commown_devices.stock_location_available_for_rent"
        )
        self.location_internal_available = self.env["stock.location"].create(
            {
                "name": "Test insernal available location",
                "usage": "internal",
                "partner_id": 1,
                "location_id": self.location_available_for_rent.id,
            }
        )

        self.quant = self.env["stock.quant"].create(
            {
                "product_id": self.lot.product_id.id,
                "lot_id": self.lot.id,
                "location_id": self.location_internal_available.id,
                "quantity": 1,
            }
        )

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
