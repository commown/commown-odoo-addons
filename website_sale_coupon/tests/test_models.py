from datetime import datetime, timedelta

from ..models.sale_order import CouponError

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

    def _create_campaign(self, name='test', **kwargs):
        kwargs['name'] = name
        kwargs.setdefault('seller_id', self.seller.id)
        kwargs.setdefault('is_without_coupons', False)
        return self.env['coupon.campaign'].create(kwargs)

    def _create_coupon(self, **kwargs):
        kwargs.setdefault('campaign_id', self.campaign.id)
        return self.env['coupon.coupon'].create(kwargs)

    def sale_order(self):
        return self.env['sale.order'].search([])[0]  # chosen SO doesn't matter

    def assertCannotCumulate(self, so, coupon_name,
                             expected_msg='Cannot cumulate those coupons'):
        with self.assertRaises(CouponError) as err:
            so.reserve_coupon(coupon_name)
        self.assertTrue(err.exception.args[0].startswith(expected_msg),
                        err.exception.args[0])

    def test_campaign_unique_name(self):
        with self.assertRaises(Exception) as err:
            self._create_campaign(name='test')
        self.assertIn('coupon_campaign_name_uniq', str(err.exception))

    def test_coupon_unique_code(self):
        self._create_coupon(code='TEST')
        with self.assertRaises(Exception) as err:
            self._create_coupon(code='TEST')
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
        so = self.sale_order()
        for coupon in coupons[:3]:
            coupon.used_for_sale_id = so.id
        self.assertEqual(self.campaign.used_coupons, 3)
        self.assertEqual(len(so.used_coupons()), 3)
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
        so = self.sale_order()
        self.assertFalse(self.campaign.is_valid(so))
        future = datetime.now().date() + timedelta(days=30)
        self.campaign.date_end = future.strftime(fields.DATE_FORMAT)

    def test_validity_product_and_qty(self):
        # Check valid when all products are eligible
        so = self.sale_order()
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
        so = self.sale_order()

        self.assertIsNone(so.reserve_coupon('DUMMYCODE'))

        coupon = self._create_coupon(code='TEST_USE')
        self.assertEqual(coupon.display_name, "TEST_USE")

        self.assertEqual(so.reserve_coupon('TEST_use'), coupon)
        self.assertIn(coupon, so.reserved_coupons())

        so.confirm_coupons()
        self.assertNotIn(coupon, so.reserved_coupons())
        self.assertEqual(coupon.used_for_sale_id, so)

    def other_product_template(self, product):
        for tmpl in self.env['product.template'].search([]):
            if tmpl.id != product.id:
                return tmpl
        else:
            assert False, 'cannot find another product template'

    def test_user_cannot_trick_confirm_coupon(self):
        """ Check users cannot confirm a coupon with a non eligible product
        (scenario where the user first added the coupon, then removed the
        eligible product before finalizing the sale) """

        assert not self.campaign.target_product_tmpl_ids

        so = self.sale_order()
        so_line = so.order_line[0]
        so_product = so_line.product_id.product_tmpl_id
        self.campaign.target_product_tmpl_ids |= so_product

        coupon = self._create_coupon(code='TEST_USE')

        # Check cannot confirm if coupon is no more valid
        self.assertEqual(so.reserve_coupon('TEST_USE'), coupon)
        so_line.product_uom_qty = 0
        so.confirm_coupons()
        self.assertFalse(coupon.used_for_sale_id)
        coupon.reserved_for_sale_id = False

        # ... although confirmation works when coupon is valid
        so_line.product_uom_qty = 1
        self.assertEqual(so.reserve_coupon('TEST_USE'), coupon)
        so.confirm_coupons()
        self.assertEqual(coupon.used_for_sale_id.id, so.id)

    def test_cumulation_rules(self):
        so = self.sale_order()

        campaign1 = self._create_campaign(
            "campaign1", can_cumulate=False, can_auto_cumulate=False)
        campaign2 = self._create_campaign(
            "campaign2", can_cumulate=False, can_auto_cumulate=False)

        coupon11 = self._create_coupon(code="TEST11", campaign_id=campaign1.id)
        coupon12 = self._create_coupon(code="TEST12", campaign_id=campaign1.id)
        coupon21 = self._create_coupon(code="TEST21", campaign_id=campaign2.id)
        coupon22 = self._create_coupon(code="TEST22", campaign_id=campaign2.id)

        self.assertEqual(so.reserve_coupon("TEST11"), coupon11)
        self.assertCannotCumulate(so, "TEST21")
        self.assertCannotCumulate(so, "TEST12", "Cannot use more than one")

        # TEST11 is reserved for so, then:
        campaign2.can_cumulate = True
        self.assertCannotCumulate(so, "TEST12", "Cannot use more than one")
        self.assertEqual(so.reserve_coupon("TEST21"), coupon21)
        self.assertCannotCumulate(so, "TEST22", "Cannot use more than one")

        # TEST11 and TEST21 are reserved for so, then:
        campaign2.can_auto_cumulate = True
        self.assertCannotCumulate(so, "TEST12", "Cannot use more than one")
        self.assertEqual(so.reserve_coupon("TEST22"), coupon22)

        # Final check:
        so.confirm_coupons()
        self.assertEqual(so.used_coupons(), coupon11 | coupon21 | coupon22)

    def test_no_need_coupon_campaign(self):
        campaign = self._create_campaign(
            name="No Coupon Test Campaign",
            is_without_coupons=True,
        )

        so = self.sale_order()
        coupon = so.reserve_coupon("NO COUPON TEST CAMPAIGN")
        self.assertTrue(coupon and coupon.campaign_id == campaign)
        so.confirm_coupons()
        self.assertEqual(coupon.used_for_sale_id, so)
        self.assertEqual(coupon.display_name, "No Coupon Test Campaign")
