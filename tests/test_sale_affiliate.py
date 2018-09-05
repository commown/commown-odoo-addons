from collections import OrderedDict

from mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SaleAffiliateTC(TransactionCase):

    def setUp(self):
        super(SaleAffiliateTC, self).setUp()

        # Insert data
        env = self.env
        seq = env.ref('website_sale_affiliate.request_sequence')
        self.affiliate = env['sale.affiliate'].create({
            'name': 'my affiliate',
            'company_id': env.ref('base.main_company').id,
            'sequence_id': seq.id,
            'valid_hours': 24,
            'valid_sales': 100,
            'gain_value': 1.,
            'gain_type': 'fixed',
            })
        self.affiliate_request = env['sale.affiliate.request'].create({
            'name': 'test affiliate request',
            'affiliate_id': self.affiliate.id,
            'date': fields.Datetime.now(),
            'ip': '127.0.0.1',
            'referrer': 'https://commown.fr',
            'user_agent': 'firefox',
            'accept_language': 'fr',
            })

        # Mock the http request object where used
        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={
            'affiliate_request': self.affiliate_request.id,
            })
        self.addCleanup(request_patcher.stop)

    def create_sale(self, create_date=None, products=None, state='sent'):
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
        self.cr.execute('UPDATE sale_order SET create_date=%s WHERE id=%s',
                        (create_date, sale.id))
        return sale

    def create_sales(self):
        prod1 = self.env.ref('product.product_product_1')  # Gap Analysis...
        prod2 = self.env.ref('product.product_product_2')  # Support Services
        prod3 = self.env.ref('product.product_product_3')  # Computer SC234
        self.create_sale('2018-01-05 12:00:00', [(prod1, 1)],
                         state='draft')
        self.create_sale('2018-01-13 12:00:00', [(prod1, 3), (prod2, 2)])
        self.create_sale('2018-02-20 12:00:00', [(prod2, 3), (prod3, 3)])
        self.create_sale('2018-02-21 12:00:00', [(prod2, 4)])
        self.create_sale('2018-03-20 12:00:00', [(prod2, 2), (prod1, 1)],
                         state='draft')
        self.create_sale('2018-03-23 12:00:00', [(prod3, 8), (prod2, 1)])
        self.create_sale('2018-04-20 12:00:00', [(prod3, 4), (prod1, 7)])

    def test_report_no_product_restriction(self):
        self.create_sales()
        self.assertEqual(OrderedDict([
            ('2018-01', OrderedDict([
                (u'GAP Analysis Service',
                 {'initiated': 4, 'validated': 3, 'gain': 3.0}),
                (u'Support Services',
                 {'initiated': 2, 'validated': 2, 'gain': 2.0}),
                 ])),
            ('2018-02', OrderedDict([
                (u'Computer SC234',
                 {'initiated': 3, 'validated': 3, 'gain': 3.0}),
                (u'Support Services',
                 {'initiated': 7, 'validated': 7, 'gain': 7.0}),
                 ])),
            ('2018-03', OrderedDict([
                (u'Computer SC234',
                 {'initiated': 8, 'validated': 8, 'gain': 8.0}),
                (u'GAP Analysis Service',
                 {'initiated': 1, 'validated': 0, 'gain': 0.0}),
                (u'Support Services',
                 {'initiated': 3, 'validated': 1, 'gain': 1.0}),
                 ])),
            ('2018-04', OrderedDict([
                (u'Computer SC234',
                 {'initiated': 4, 'validated': 4, 'gain': 4.0}),
                (u'GAP Analysis Service',
                 {'initiated': 7, 'validated': 7, 'gain': 7.0}),
                 ])),
            ]), self.affiliate.report_data())

    def test_report_with_product_restriction(self):

        self.affiliate.restriction_product_tmpl_ids |= (
            self.env.ref('product.product_product_1').product_tmpl_id |
            self.env.ref('product.product_product_2').product_tmpl_id)

        self.create_sales()

        # Add a sale that should not even be attached to the affiliate request
        # (not a selected product)
        prod3 = self.env.ref('product.product_product_3')
        self.create_sale('2018-05-20 12:00:00', [(prod3, 3)])

        self.assertEqual(OrderedDict([
            ('2018-01', OrderedDict([
                (u'GAP Analysis Service',
                 {'initiated': 4, 'validated': 3, 'gain': 3.0}),
                (u'Support Services',
                 {'initiated': 2, 'validated': 2, 'gain': 2.0}),
                 ])),
            ('2018-02', OrderedDict([
                (u'GAP Analysis Service',
                 {'initiated': 0, 'validated': 0, 'gain': 0.0}),
                (u'Support Services',
                 {'initiated': 7, 'validated': 7, 'gain': 7.0}),
                 ])),
            ('2018-03', OrderedDict([
                (u'GAP Analysis Service',
                 {'initiated': 1, 'validated': 0, 'gain': 0.0}),
                (u'Support Services',
                 {'initiated': 3, 'validated': 1, 'gain': 1.0}),
                 ])),
            ('2018-04', OrderedDict([
                (u'GAP Analysis Service',
                 {'initiated': 7, 'validated': 7, 'gain': 7.0}),
                (u'Support Services',
                 {'initiated': 0, 'validated': 0, 'gain': 0.0}),
                 ])),
            ]), self.affiliate.report_data())

    def test_report_percentage_gain_type(self):

        self.affiliate.gain_type = 'percentage'
        self.affiliate.gain_value = 10.

        prod1 = self.env.ref('product.product_product_1')
        prod2 = self.env.ref('product.product_product_2')
        self.create_sale('2018-01-05 12:00:00', [(prod1, 3), (prod2, 5)])

        data = self.affiliate.report_data()

        expected_gain1 = 3 * 10./100 * prod1.list_price
        self.assertAlmostEqual(
            data.get('2018-01', {}).get('GAP Analysis Service', {})['gain'],
            expected_gain1)

        expected_gain2 = 5 * 10./100 * prod2.list_price
        self.assertAlmostEqual(
            data.get('2018-01', {}).get('Support Services', {}).get('gain'),
            expected_gain2)
