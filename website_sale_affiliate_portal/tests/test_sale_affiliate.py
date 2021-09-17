from collections import OrderedDict

from odoo.tests.common import at_install, post_install

from odoo.addons.website_sale_affiliate_product_restriction.tests import common


@at_install(False)
@post_install(True)
class SaleAffiliateTC(common.AffiliateTC):

    def setUp(self):
        super(SaleAffiliateTC, self).setUp()

    def create_sales(self):
        p1 = self.env.ref('product.product_product_1')  # Gap Analysis...
        p2 = self.env.ref('product.product_product_2')  # Support Services
        p3 = self.env.ref('product.product_product_3')  # Computer SC234

        sess = self.fake_session
        sess['affiliate_request'] = self.create_affiliate_req('2018-01-05').id
        self.create_sale([(p1, 1)], 'draft', create_date='2018-01-05')

        sess['affiliate_request'] = self.create_affiliate_req('2018-01-13').id
        self.create_sale([(p1, 3), (p2, 2)], create_date='2018-01-13')

        sess['affiliate_request'] = self.create_affiliate_req('2018-02-20').id
        self.create_sale([(p2, 3), (p3, 3)], create_date='2018-02-20')
        self.create_sale([(p2, 4)], create_date='2018-02-21')

        sess['affiliate_request'] = self.create_affiliate_req('2018-03-20').id
        self.create_sale([(p2, 2), (p1, 1)], 'draft', create_date='2018-03-20')
        self.create_sale([(p3, 8), (p2, 1)], create_date='2018-03-20')

        sess['affiliate_request'] = self.create_affiliate_req('2018-04-20').id
        self.create_sale([(p3, 4), (p1, 7)], create_date='2018-04-20')

        sess['affiliate_request'] = self.create_affiliate_req('2018-05-03').id

    def test_report_no_product_restriction(self):
        self.affiliate.gain_type = 'fixed'
        self.affiliate.gain_value = 1

        self.create_sales()

        self.assertEqual(OrderedDict([
            ('2018-01', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 3, 'gain': 3.0}),
                    (u'Support Services', {'validated': 2, 'gain': 2.0}),
                    ])),
                ('visits', 2)])),
            ('2018-02', OrderedDict([
                ('by-product', OrderedDict([
                    (u'Computer SC234', {'validated': 3, 'gain': 3.0}),
                    (u'Support Services', {'validated': 7, 'gain': 7.0}),
                    ])),
                ('visits', 1)])),
            ('2018-03', OrderedDict([
                ('by-product', OrderedDict([
                    (u'Computer SC234', {'validated': 8, 'gain': 8.0}),
                    (u'Support Services', {'validated': 1, 'gain': 1.0}),
                    ])),
                ('visits', 1)])),
            ('2018-04', OrderedDict([
                ('by-product', OrderedDict([
                    (u'Computer SC234', {'validated': 4, 'gain': 4.0}),
                    (u'GAP Analysis Service', {'validated': 7, 'gain': 7.0}),
                    ])),
                ('visits', 1)])),
            ('2018-05', {
                'by-product': {'-': {'validated': 0, 'gain': 0.0}},
                'visits': 1}),
         ]), self.affiliate.report_data())

    def test_report_with_product_restriction(self):

        self.affiliate.restriction_product_tmpl_ids |= (
            self.env.ref('product.product_product_1').product_tmpl_id |
            self.env.ref('product.product_product_2').product_tmpl_id)

        self.affiliate.gain_type = 'fixed'
        self.affiliate.gain_value = 1
        self.create_sales()

        # Add a sale that should not even be attached to the affiliate request
        # (not a selected product)
        p3 = self.env.ref('product.product_product_3')
        self.create_sale([(p3, 3)], create_date='2018-05-20')

        self.assertEqual(OrderedDict([
            ('2018-01', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 3, 'gain': 3.0}),
                    (u'Support Services', {'validated': 2, 'gain': 2.0}),
                    ])),
                ('visits', 2)])),
            ('2018-02', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 0, 'gain': 0.0}),
                    (u'Support Services', {'validated': 7, 'gain': 7.0}),
                    ])),
                ('visits', 1)])),
            ('2018-03', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 0, 'gain': 0.0}),
                    (u'Support Services', {'validated': 1, 'gain': 1.0}),
                    ])),
                ('visits', 1)])),
            ('2018-04', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 7, 'gain': 7.0}),
                    (u'Support Services', {'validated': 0, 'gain': 0.0}),
                    ])),
                ('visits', 1)])),
            ('2018-05', OrderedDict([
                ('by-product', OrderedDict([
                    (u'GAP Analysis Service', {'validated': 0, 'gain': 0.0}),
                    (u'Support Services', {'validated': 0, 'gain': 0.0}),
                    ])),
                ('visits', 1)])),
            ]), self.affiliate.report_data())

    def test_report_percentage_gain_type(self):

        self.affiliate.gain_type = 'percentage'
        self.affiliate.gain_value = 10.

        p1 = self.env.ref('product.product_product_1')
        p2 = self.env.ref('product.product_product_2')

        self.fake_session['affiliate_request'] = self.create_affiliate_req().id
        self.create_sale([(p1, 3), (p2, 5)], create_date='2018-01-05')

        data = self.affiliate.report_data()

        expected_gain1 = 3 * 10./100 * p1.list_price
        self.assertAlmostEqual(
            data.get('2018-01', {}).get('by-product', {}).get(
                'GAP Analysis Service', {}).get('gain', 0),
            expected_gain1)

        expected_gain2 = 5 * 10./100 * p2.list_price
        self.assertAlmostEqual(
            data.get('2018-01', {}).get('by-product', {}).get(
                'Support Services', {}).get('gain', 0),
            expected_gain2)
