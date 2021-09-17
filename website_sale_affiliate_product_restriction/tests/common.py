from mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class AffiliateTC(TransactionCase):

    def setUp(self):
        super(AffiliateTC, self).setUp()
        seq = self.env.ref('website_sale_affiliate.request_sequence')
        self.affiliate = self.env['sale.affiliate'].create({
            'name': 'my affiliate',
            'company_id': self.env.ref('base.main_company').id,
            'sequence_id': seq.id,
            'valid_hours': 24,
            'valid_sales': 100,
            })
        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={})
        self.fake_session = request_mock.session
        self.addCleanup(request_patcher.stop)

    def create_affiliate_req(self, create_date=None):
        req = self.env['sale.affiliate.request'].create({
            'name': 'test affiliate request',
            'affiliate_id': self.affiliate.id,
            'date': fields.Datetime.now(),
            'ip': '127.0.0.1',
            'referrer': 'https://commown.fr',
            'user_agent': 'firefox',
            'accept_language': 'fr',
            })
        if create_date is not None:
            self.cr.execute(
                'UPDATE sale_affiliate_request SET create_date=%s WHERE id=%s',
                (create_date, req.id))
        return req

    def create_sale(self, products=None, state='sent', create_date=None):
        env = self.env
        partner = env.ref('base.res_partner_1')
        if products is None:
            products = [env.ref('product.product_product_1'), 1]
        data = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'pricelist_id': env.ref('product.list0').id,
            'state': state,
            'order_line': [],
            }
        for product, qty in products:
            data['order_line'].append((0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price,
                }))
        sale = self.env['sale.order'].create(data)
        if create_date is not None:
            self.cr.execute('UPDATE sale_order SET create_date=%s WHERE id=%s',
                            (create_date, sale.id))

        return sale
