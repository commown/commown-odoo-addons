from odoo.exceptions import UserError

from .common import DeviceAsAServiceTC


class ContractTC(DeviceAsAServiceTC):
    def test_cant_send_ungraded_lot(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        lot = self.adjust_stock(grade_lot=False)
        with self.assertRaises(UserError) as err:
            contract.send_devices(lot, {})
        self.assertIn("Please set the grade on lots", err.exception.name)

    def test_compute_lot_number(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        init_lot_nb = contract.lot_nb

        lot = self.adjust_stock(grade_lot=False)
        contract.lot_ids |= lot
        self.assertEqual(contract.lot_nb, init_lot_nb + 1)

        contract.lot_ids = False
        self.assertEqual(contract.lot_nb, init_lot_nb)
