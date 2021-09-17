from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class DeviceAsAServiceTC(RentalSaleOrderTC):

    def setUp(self):
        super(DeviceAsAServiceTC, self).setUp()

        partner = self.env.ref('portal.demo_user0_res_partner')
        contract_tmpl = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(1, '1 month Fairphone premium',
                                   self.get_default_tax()),
                self._invoice_line(1, 'Accessory: ##ACCESSORY##',
                                   self.get_default_tax()),
                ])
        self.storable_product = self.env['product.template'].create({
            'name': u'Fairphone 3', 'type': u'product', 'tracking': u'serial',
        })
        team = self.env.ref('sales_team.salesteam_website_sales')
        sold_product = self._create_rental_product(
            name='Fairphone as a Service',
            list_price=60., rental_price=30.,
            contract_template_id=contract_tmpl.id,
            storable_product_id=self.storable_product.product_variant_id.id,
            followup_sales_team_id=team.id,
        )

        oline = self._oline(sold_product, product_uom_qty=3)
        self.so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [oline],
        })
        self.so.action_confirm()

    def adjust_stock(self, product=None, qty=1., serial=u'serial-0',
                     location=None, date="2000-01-01"):
        if product is None:
            product = self.storable_product.product_variant_id
        lot = self.env['stock.production.lot'].create({
            'name': serial,
            'product_id': product.id,
        })
        location = location or self.env.ref(
            'commown_devices.stock_location_fp3_new')

        old_quants = self.env["stock.quant"].search([])
        product_qty = self.env['stock.change.product.qty'].create({
            'location_id': location.id,
            'product_id': product.id,
            'new_quantity': qty,
            'lot_id': lot.id,
        })
        product_qty.change_product_qty()
        new_quants = self.env["stock.quant"].search([]) - old_quants
        self.env.cr.execute(
            "UPDATE stock_quant SET in_date=%(date)s WHERE id in %(ids)s",
            {"date": date, "ids": tuple(new_quants.ids)})
        self.env.cache.clear()
        return lot
