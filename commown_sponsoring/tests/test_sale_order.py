from odoo import Command

from odoo.addons.website_sale_coupon.models.sale_order import CouponError

from .common import SponsoringTC


class SponsoringSaleTC(SponsoringTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.create_contract(cls.partner)
        cls.contract.date_start = "2026-01-01"

        cls.contract_2 = cls.create_contract(cls.partner_2)
        cls.contract_2.date_start = "2026-01-01"

        cls.demo_partner = cls.env.ref("base.partner_demo")
        cls.product = cls.env.ref("product_rental.prod_fp")
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

    def test_reserved_sponsor_code_usage_limit(self):
        "A customer who already reserved a sponsoring code cannot use another"
        self.so.reserve_coupon(self.partner.sponsor_code)

        with self.assertRaises(CouponError) as exc:
            self.so.reserve_coupon(self.partner_2.sponsor_code)
        self.assertIn("code in this order", exc.exception.args[0])

    def test_used_sponsor_code_usage_limit(self):
        "A customer who already used a sponsoring code cannot use another"
        self.so.reserve_coupon(self.partner.sponsor_code)
        self.so.action_confirm()
        so2 = self.env["sale.order"].create(
            {
                "name": "Dummy Sale Order",
                "partner_id": self.demo_partner.id,
                "date_order": "2026-06-01",
            }
        )

        with self.assertRaises(CouponError) as exc:
            so2.reserve_coupon(self.partner_2.sponsor_code)

        self.assertIn("code on a previous order", exc.exception.args[0])

    def _trigger_sponsor_msg_action(self):
        auto = self.env.ref(
            "commown_sponsoring.automation_send_sponsor_notification_email"
        )
        auto.last_run = False
        auto._check()

    def test_sponsor_confirmation_email_to_sponsor_ok(self):
        "Whenever a sponsor code is used, its sponsor should be notified"
        self.so.reserve_coupon(self.partner.sponsor_code)
        self.so.action_confirm()

        new_contract = self.env["contract.contract"].of_sale(self.so)
        new_contract.date_start = "2026-03-01"

        self._trigger_sponsor_msg_action()
        confirm_msg = self.partner.message_ids

        self.assertEqual(self.partner, confirm_msg.notified_partner_ids)
        self.assertIn(self.demo_partner.name, confirm_msg.body)

    def test_sponsor_confirmation_email_to_sponsor_cancelled_early(self):
        "If a new contract with a sponsor code is cancelled early, no notification mail should be sent"
        self.so.reserve_coupon(self.partner.sponsor_code)
        self.so.action_confirm()

        new_contract = self.env["contract.contract"].of_sale(self.so)
        new_contract.date_start = "2026-03-01"
        new_contract.date_end = "2026-03-10"

        self._trigger_sponsor_msg_action()
        self.assertFalse(self.partner.message_ids)
