from mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SaleOrderTC(TransactionCase):

    def setUp(self):
        super(SaleOrderTC, self).setUp()
        env = self.env
        seq = env.ref('website_sale_affiliate.request_sequence')
        self.affiliate = env['sale.affiliate'].create({
            'name': 'my affiliate',
            'company_id': env.ref('base.main_company').id,
            'sequence_id': seq.id,
            'valid_hours': 24,
            'valid_sales': 100,
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
        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={
            'affiliate_request': self.affiliate_request.id,
            })
        self.addCleanup(request_patcher.stop)

    def sale_product1(self):
        env = self.env
        partner = env.ref('base.res_partner_1')
        product = env.ref('product.product_product_1')
        return self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [(0, 0, {'name': product.name,
                                   'product_id': product.id,
                                   'product_uom_qty': 1,
                                   'product_uom': product.uom_id.id,
                                   'price_unit': product.list_price})],
            'pricelist_id': env.ref('product.list0').id,
            })

    def test_sale_order_no_restriction(self):
        so = self.sale_product1()
        self.assertEqual(so.affiliate_request_id.id, self.affiliate_request.id)

    def test_sale_order_restriction_and_invalid_product(self):
        p2 = self.env.ref('product.product_product_2').product_tmpl_id
        p3 = self.env.ref('product.product_product_3').product_tmpl_id
        self.affiliate.restriction_product_tmpl_ids |= (p2 | p3)
        so = self.sale_product1()
        self.assertFalse(so.affiliate_request_id.id)

    def test_sale_order_restriction_and_valid_product(self):
        p1 = self.env.ref('product.product_product_1').product_tmpl_id
        p2 = self.env.ref('product.product_product_2').product_tmpl_id
        self.affiliate.restriction_product_tmpl_ids |= (p1 | p2)
        so = self.sale_product1()
        self.assertEqual(so.affiliate_request_id.id, self.affiliate_request.id)
