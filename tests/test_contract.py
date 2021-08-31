from .common import DeviceAsAServiceTC

from ..models.common import do_new_transfer


class ContractTC(DeviceAsAServiceTC):

    def test_stock_at_date(self):
        loc_check = self.env.ref("commown_devices.stock_location_fp3_to_check")

        lot1 = self.adjust_stock(serial=u"my-fp3-1")
        quant1 = self.env["stock.quant"].search([("lot_id", "=", lot1.id)])

        lot2 = self.adjust_stock(serial=u"my-fp3-2")
        quant2 = self.env["stock.quant"].search([("lot_id", "=", lot2.id)])

        contract = self.so.order_line[0].contract_id

        contract.send_device(quant1, "2021-07-01 17:00:00", do_transfer=True)
        contract.send_device(quant2, "2021-07-14", do_transfer=True)
        return_picking = contract.receive_device(
            lot1, loc_check, "2021-07-22", do_transfer=False)

        self.assertFalse(contract.stock_at_date("2021-07-01 16:59:59"))
        self.assertEqual(contract.stock_at_date("2021-07-01 17:00:01"), lot1)
        self.assertEqual(contract.stock_at_date("2021-07-20"), lot1 | lot2)

        # Check that until the picking is done, the stock stays as is:
        self.assertEqual(contract.stock_at_date("2021-07-25"), lot1 | lot2)
        do_new_transfer(return_picking, "2021-07-22")
        self.assertEqual(contract.stock_at_date("2021-07-25"), lot2)
