from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class DeviceAsAServiceTC(RentalSaleOrderTC):

    def setUp(self):
        super(DeviceAsAServiceTC, self).setUp()

        partner = self.env.ref('portal.demo_user0_res_partner')
        contract_tmpl = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(1, '1 month Fairphone premium',
                                   self.get_default_tax()),
                ])
        stockable_product = self.env['product.template'].create({
            'name': u'Fairphone 3', 'type': u'product', 'tracking': u'serial',
        })
        team = self.env.ref('sales_team.salesteam_website_sales')
        sold_product = self._create_rental_product(
            name='Fairphone as a Service',
            list_price=60., rental_price=30.,
            contract_template_id=contract_tmpl.id,
            stockable_product_id=stockable_product.product_variant_id.id,
            followup_sales_team_id=team.id,
        )

        oline = self._oline(sold_product)
        self.so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [oline],
        })
        self.so.action_confirm()