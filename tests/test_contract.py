from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class ContractTC(RentalSaleOrderTC):

    def setUp(self):
        super(ContractTC, self).setUp()

        partner = self.env.ref('portal.demo_user0_res_partner')
        contract_tmpl = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(1, '1 month Fairphone premium',
                                   self.get_default_tax()),
                ])
        stockable_product = self.env['product.template'].create({
            'name': u'Fairphone 3', 'type': u'product', 'tracking': u'serial',
        })
        sold_product = self._create_rental_product(
            name='Fairphone as a Service',
            list_price=60., rental_price=30.,
            contract_template_id=contract_tmpl.id,
            stockable_product_id=stockable_product.product_variant_id.id)

        oline = self._oline(sold_product)
        self.so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [oline],
        })
        self.so.action_confirm()

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
