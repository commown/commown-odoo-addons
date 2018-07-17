from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import ValidationError, AccessError
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class CouponSchemaTC(TransactionCase):

    def setUp(self):
        super(CouponSchemaTC, self).setUp()
        self.seller = self.env.ref('base.res_partner_2')
        self.campaign = self._create_campaign()

    def _create_campaign(self, name=u'test', **kwargs):
        kwargs['name'] = name
        kwargs.setdefault('seller_id', self.seller.id)
        return self.env['coupon.campaign'].create(kwargs)

    def _create_coupon(self, **kwargs):
        kwargs.setdefault('campaign_id', self.campaign.id)
        return self.env['coupon.coupon'].create(kwargs)

    def test_campaign_unique_name(self):
        with self.assertRaises(Exception) as err:
            self._create_campaign(name=u'test')
        self.assertIn('coupon_campaign_name_uniq', str(err.exception))

    def test_coupon_unique_code(self):
        self._create_coupon(code=u'TEST')
        with self.assertRaises(Exception) as err:
            self._create_coupon(code=u'TEST')
        self.assertIn('coupon_coupon_code_uniq', str(err.exception))

    def test_campaign_dates_check_1(self):
        with self.assertRaises(ValidationError) as err:
            self.campaign.update({'date_start': '2018-03-01',
                                  'date_end': '2018-02-01'})
        self.assertEqual(err.exception.args[0],
                         'Start date must be before end date')

    def test_campaign_dates_check_2(self):
        self.campaign.update({'date_start': '2035-01-01'})
        self.campaign.update({'date_end': '2036-01-01'})
        with self.assertRaises(ValidationError) as err:
            self.campaign.update({'date_end': '2018-01-01'})
        self.assertEqual(err.exception.args[0],
                         'Start date must be before end date')

    def test_number_of_coupons(self):
        self.assertEqual(self.campaign.emitted_coupons, 0)
        coupons = [self._create_coupon(campaign_id=self.campaign.id)
                   for _i in range(5)]
        self.assertEqual(self.campaign.emitted_coupons, len(coupons))
        so = self.env['sale.order'].search([])[0]  # chosen SO does not matter
        for coupon in coupons[:3]:
            coupon.used_for_sale_id = so.id
        self.assertEqual(self.campaign.used_coupons, 3)
        self.assertEqual(self.campaign.emitted_coupons, len(coupons))

    def test_security_read(self):
        self.assertTrue(self.env['coupon.campaign'].search([]))
        someone = self.env.ref('base.res_partner_1')
        with self.assertRaises(AccessError):
            Campaign = self.env['coupon.campaign'].sudo(someone)
            self.assertFalse(Campaign.search([]))

    def test_validity_date(self):
        self.campaign.update({'date_start': '2018-01-01',
                              'date_end': '2018-02-01'})
        so = self.env['sale.order'].search([])[0]  # chosen SO does not matter
        self.assertFalse(self.campaign.is_valid(so))
        future = datetime.now().date() + timedelta(days=30)
        self.campaign.date_end = future.strftime(fields.DATE_FORMAT)

    def test_validity_product_and_qty(self):
        # Check valid when all products are eligible
        so = self.env['sale.order'].search([])[0]  # chosen SO does not matter
        assert not self.campaign.target_product_tmpl_ids
        self.assertTrue(self.campaign.is_valid(so))

        # Check invalid when sale product not eligible
        so_product_tmpl = so.order_line[0].product_id.product_tmpl_id
        for tmpl in self.env['product.template'].search([]):
            if tmpl.id != so_product_tmpl.id:
                self.campaign.target_product_tmpl_ids |= tmpl
                break
        else:
            assert False, 'cannot find another product template'
        self.assertFalse(self.campaign.is_valid(so))

        # Check valid when sale product is eligible
        self.campaign.target_product_tmpl_ids |= so_product_tmpl
        self.assertTrue(self.campaign.is_valid(so))

        # ... unless the quantity is zero
        so.order_line[0].product_uom_qty = 0
        self.assertFalse(self.campaign.is_valid(so))

    def test_reserve_and_confirm_coupon(self):
        so = self.env['sale.order'].search([])[0]  # chosen SO does not matter
        Coupon = self.env['coupon.coupon']

        self.assertIsNone(Coupon.reserve_coupon(u'DUMMYCODE', so))

        coupon = self._create_coupon(code=u'TEST_USE')
        self.assertEqual(Coupon.reserve_coupon(u'TEST_USE', so), coupon)
        self.assertIn(coupon, Coupon.reserved_coupons(so))

        coupon.confirm_coupons()
        self.assertNotIn(coupon, Coupon.reserved_coupons(so))
        self.assertEqual(coupon.used_for_sale_id, so)

    def other_product_template(self, product):
        for tmpl in self.env['product.template'].search([]):
            if tmpl.id != product.id:
                return tmpl
        else:
            assert False, 'cannot find another product template'

    def sale_order(self):
        return self.env['sale.order'].search([])[0]  # chosen SO does not matter

    def test_user_cannot_trick_confirm_coupon(self):
        """ Check users cannot confirm a coupon with a non eligible product
        (scenario where the user first added the coupon, then removed the
        eligible product before finalizing the sale) """

        assert not self.campaign.target_product_tmpl_ids
        Coupon = self.env['coupon.coupon']

        so = self.sale_order()
        so_line = so.order_line[0]
        so_product = so_line.product_id.product_tmpl_id
        self.campaign.target_product_tmpl_ids |= so_product

        coupon = self._create_coupon(code=u'TEST_USE')

        # Check cannot confirm if coupon is no more valid
        self.assertEqual(Coupon.reserve_coupon(u'TEST_USE', so), coupon)
        so_line.product_uom_qty = 0
        coupon.confirm_coupons()
        self.assertFalse(coupon.used_for_sale_id)
        self.assertFalse(coupon.reserved_for_sale_id)

        # ... although confirmation works when coupon is valid
        so_line.product_uom_qty = 1
        self.assertEqual(Coupon.reserve_coupon(u'TEST_USE', so), coupon)
        coupon.confirm_coupons()
        self.assertEqual(coupon.used_for_sale_id.id, so.id)
