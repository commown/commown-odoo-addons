from odoo import Command

from odoo.addons.website_sale_coupon.models.sale_order import CouponError

from .common import SponsoringTC


class SponsoringSaleTC(SponsoringTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.create_contract(cls.partner)
        cls.contract.date_start = "2026-01-01"

        cls.demo_partner = cls.env.ref("base.partner_demo")
        cls.product = cls.env.ref("product.product_product_1")
        cls.so = cls.env["sale.order"].create(
            {
                "name": "Dummy Sale Order",
                "partner_id": cls.demo_partner.id,
                "date_order": "2026-02-01",
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom": cls.product.uom_id.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )


class SponsoringSaleOrderTC(SponsoringSaleTC):
    def test_use_sponsor_code_ok(self):
        "Using a sponsor code while at least one of the origin partner's contract is active should be accepted"
        coupon = self.so.reserve_coupon(self.partner.sponsor_code)
        self.assertTrue(coupon)

    def test_no_sponsor_code_disabled_w_no_contracts(self):
        "Using a sponsor code while none of the origin partner's contracts are active should be refused"
        self.contract.date_end = "2026-03-01"
        with self.assertRaises(CouponError) as exc:
            self.so.reserve_coupon(self.partner.sponsor_code)

        self.assertIn("code is currently inactive", exc.exception.args[0])
