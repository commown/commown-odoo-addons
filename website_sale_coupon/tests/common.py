from ..models.sale_order import CouponError


class CouponTestMixin:
    "Common class for coupon related tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seller = cls.env.ref("base.res_partner_2")
        cls.campaign = cls._create_campaign()

    @classmethod
    def _create_campaign(cls, name="test", **kwargs):
        kwargs["name"] = name
        kwargs.setdefault("seller_id", cls.seller.id)
        kwargs.setdefault("is_without_coupons", False)
        return cls.env["coupon.campaign"].create(kwargs)

    def _create_coupon(self, **kwargs):
        kwargs.setdefault("campaign_id", self.campaign.id)
        return self.env["coupon.coupon"].create(kwargs)

    def sale_order(self):
        return self.env["sale.order"].search([])[0]  # chosen SO doesn't matter

    def assertCannotCumulate(
        self, so, coupon_name, expected_msg="Cannot cumulate those coupons"
    ):
        with self.assertRaises(CouponError) as err:
            so.reserve_coupon(coupon_name)
        self.assertTrue(
            err.exception.args[0].startswith(expected_msg), err.exception.args[0]
        )
