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
