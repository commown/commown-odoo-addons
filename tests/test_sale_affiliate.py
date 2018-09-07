from mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SaleAffiliateTC(TransactionCase):

    def setUp(self):
        super(SaleAffiliateTC, self).setUp()
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

    def create_affiliate_req(self):
        return self.env['sale.affiliate.request'].create({
            'name': 'test affiliate request',
            'affiliate_id': self.affiliate.id,
            'date': fields.Datetime.now(),
            'ip': '127.0.0.1',
            'referrer': 'https://commown.fr',
            'user_agent': 'firefox',
            'accept_language': 'fr',
            })

    def create_sale(self, products=None, state='sent'):
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
        return sale

    def test_sale_order_without_product_restriction(self):
        p1 = self.env.ref('product.product_product_1').product_tmpl_id
        p2 = self.env.ref('product.product_product_2').product_tmpl_id
        p3 = self.env.ref('product.product_product_3').product_tmpl_id

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.create_sale([(p1, 1), (p2, 1)], 'sent')

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.create_sale([(p2, 1), (p3, 1)], 'draft')
        self.create_sale([(p3, 1)], 'sent')
        self.create_sale([(p1, 1)], 'sent')
        self.create_sale([(p2, 1)], 'sent')

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.fake_session['affiliate_request'] = self.create_affiliate_req().id

        self.assertAlmostEqual(self.affiliate.sales_per_request, 1)
        self.assertAlmostEqual(self.affiliate.conversion_rate, 0.5)

    def test_sale_order_with_product_restriction(self):
        p1 = self.env.ref('product.product_product_1').product_tmpl_id
        p2 = self.env.ref('product.product_product_2').product_tmpl_id
        p3 = self.env.ref('product.product_product_3').product_tmpl_id
        self.affiliate.restriction_product_tmpl_ids |= (p2 | p3)

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.create_sale([(p1, 1)], 'sent')

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.create_sale([(p1, 1), (p3, 1)], 'sent')
        self.create_sale([(p2, 1)], 'sent')

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.fake_session['affiliate_request'] = self.create_affiliate_req().id

        self.assertEqual(self.affiliate.sales_per_request, 0.5)
        self.assertAlmostEqual(self.affiliate.conversion_rate, 0.25)
