from .common import DeviceAsAServiceTC

from ..models.common import do_new_transfer


class ContractTC(DeviceAsAServiceTC):

    def test_send_all_picking(self):
        """Calling contract `send_all_picking` creates a confirmed picking and
        the partner's location, if not yet done"""

        # Add another storable product on contract to check all products move:
        accessory_storable = self.env["product.template"].create({
            "name": u"Charger", "type": u"product", "tracking": u"serial",
        })
        accessory_usage = self._create_rental_product(
            name="Charger usage", list_price=2., rental_price=1.,
            storable_product_id=accessory_storable.product_variant_id.id,
            contract_template_id=False,
        )
        main_product = self.so.product_id
        main_product.accessory_product_ids |= accessory_usage

        oline1 = self._oline(main_product)
        oline2 = self._oline(accessory_usage)
        so = self.env["sale.order"].create({
            "partner_id": self.so.partner_id.id,
            "partner_invoice_id": self.so.partner_id.id,
            "partner_shipping_id": self.so.partner_id.id,
            "order_line": [oline1, oline2],
        })
        so.action_confirm()

        contract = so.order_line.mapped("contract_id")
        self.assertEqual(len(contract), 1,
                         "Prequisite failure: main product and its accessory"
                         " must have the same contract.")
        self.assertEqual(len(contract.recurring_invoice_line_ids), 2,
                         "Prerequisite failure: contract should 2 invoice lines"
                         " (1 for the main product, 1 for the accessory)")

        # Check picking
        picking = contract.send_all_picking()

        self.assertEqual(picking.state, "confirmed")
        self.assertEqual(picking.origin, contract.name)
        self.assertEqual(picking.move_lines.mapped("product_id.name"),
                         [u"Fairphone 3", u"Charger"])

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
