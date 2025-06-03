from datetime import datetime

from odoo.exceptions import UserError

from .common import DeviceAsAServiceTC


class ContractTC(DeviceAsAServiceTC):
    def test_cant_send_ungraded_lot(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        lot = self.adjust_stock(grade_lot=False)
        with self.assertRaises(UserError) as err:
            contract.send_devices(lot, {})
        self.assertIn("Please set the grade on lots", err.exception.args[0])

    def test_compute_lot_number(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        init_lot_nb = contract.lot_nb

        lot = self.adjust_stock()
        contract.lot_ids |= lot
        self.assertEqual(contract.lot_nb, init_lot_nb + 1)

        contract.lot_ids = False
        self.assertEqual(contract.lot_nb, init_lot_nb)

    def test_partner_location_changed(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        partner = contract.partner_id
        lot = self.adjust_stock()
        scheduled_date = datetime.strptime("2003-03-03", "%Y-%m-%d")

        send_pick = contract.send_devices(lot, {}).picking_id
        send_pick.scheduled_date = scheduled_date
        send_pick.button_validate()

        receive_loc = self.env.ref("commown_devices.stock_location_devices_to_check")
        return_pick = contract.receive_devices(lot, {}, receive_loc).picking_id
        return_pick.scheduled_date = scheduled_date

        old_part_loc = partner.get_customer_locations(usage="internal")

        contract._partner_location_changed()
        self.assertEqual(send_pick.location_dest_id, old_part_loc)
        self.assertEqual(return_pick.location_id, old_part_loc)

        old_part_loc.partner_id = False
        new_part_loc = partner.get_or_create_customer_location(contract.stock_ownership)
        self.assertNotEqual(old_part_loc, new_part_loc)
        contract._partner_location_changed(old_part_loc)
        self.assertEqual(send_pick.location_dest_id, new_part_loc)
        self.assertEqual(return_pick.location_id, new_part_loc)

        self.assertEqual(send_pick.date_done, scheduled_date)
        self.assertNotEqual(return_pick.date_done, scheduled_date)
