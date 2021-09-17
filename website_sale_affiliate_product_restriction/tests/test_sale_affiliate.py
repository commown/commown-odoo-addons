from odoo.tests.common import at_install, post_install

from common import AffiliateTC


@at_install(False)
@post_install(True)
class SaleAffiliateTC(AffiliateTC):

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
