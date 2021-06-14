from .common import DeviceAsAServiceTC


class ContractTC(DeviceAsAServiceTC):

    def test_send_all_picking_and_create_partner_location(self):
        """Calling contract `send_all_picking` creates a confirmed picking and
        the partner's location, if not yet done"""
        contract = self.so.order_line.contract_id
        picking = contract.send_all_picking()

        self.assertEqual(picking.state, 'confirmed')
        self.assertEqual(picking.origin, contract.name)

        location = contract.partner_id.property_stock_customer
        self.assertEqual(location.name, contract.partner_id.name)
        self.assertEqual(location.location_id,
                         self.env.ref('stock.stock_location_customers'))
        # Check set_customer_location idempotency:
        self.assertEqual(location, contract.partner_id.set_customer_location())
