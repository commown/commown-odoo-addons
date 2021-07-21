from .common import DeviceAsAServiceTC


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
            stockable_product_id=accessory_storable.product_variant_id.id,
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
