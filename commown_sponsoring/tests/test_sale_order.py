from freezegun import freeze_time
from lxml import html

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
        cls.partner_2 = cls.partner.copy({"email": "test@test.com"})
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
        cls.so_2 = cls.so.copy({"partner_id": cls.partner_2.id})

    def _reserve_coupon_and_confirm(self, so):
        so.reserve_coupon(self.partner.sponsor_code)
        so.action_confirm()


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
        self._reserve_coupon_and_confirm(self.so)
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

    def _trigger_sponsor_msg_cron(self, lastcall=False):
        cron = self.env.ref(
            "commown_sponsoring.cron_send_sponsorship_notification_mail"
        )
        if lastcall:  # pragma: no cover
            cron.lastcall = lastcall
        cron.method_direct_trigger()

    def _get_contract_names_from_mail(self, message):
        doc = html.fromstring(message.body)
        return doc.xpath("//li/text()")

    def test_sponsor_confirmation_email_ok_one_person(self):
        """
        The cron should only send emails for contracts starting between now and the previous cron call
        (minus for the withdrawal period days on both)
        """
        self._reserve_coupon_and_confirm(self.so)
        self._reserve_coupon_and_confirm(self.so_2)

        c1 = self.env["contract.contract"].of_sale(self.so)
        c2 = self.env["contract.contract"].of_sale(self.so_2)

        c1.date_start = "2026-03-01"
        c2.date_start = "2026-03-02"

        with freeze_time("2026-03-15 14:00:00"):
            self._trigger_sponsor_msg_cron()
        self.assertFalse(self.partner.message_ids)

        with freeze_time("2026-03-16 14:00:00"):
            self._trigger_sponsor_msg_cron()
        confirm_msg = self.partner.message_ids

        self.assertEqual(self.partner, confirm_msg.notified_partner_ids)
        self.assertEqual([c1.name], self._get_contract_names_from_mail(confirm_msg))

        with freeze_time("2026-03-17 14:00:00"):
            self._trigger_sponsor_msg_cron()

        confirm_msg_2 = self.partner.message_ids - confirm_msg

        self.assertEqual(self.partner, confirm_msg_2.notified_partner_ids)
        self.assertEqual([c2.name], self._get_contract_names_from_mail(confirm_msg_2))

    def test_sponsor_confirmation_email_ok_multiple_people(self):
        "Multiple contracts with a sponsor starting on the same day should only lead to one notif. mail"
        self._reserve_coupon_and_confirm(self.so)
        self._reserve_coupon_and_confirm(self.so_2)

        c1 = self.env["contract.contract"].of_sale(self.so)
        c2 = self.env["contract.contract"].of_sale(self.so_2)

        c1.date_start = "2026-03-01"
        c2.date_start = "2026-03-01"

        self.env["contract.contract"].invalidate_model()
        self._trigger_sponsor_msg_cron()
        confirm_msg = self.partner.message_ids

        self.assertEqual(len(confirm_msg), 1)
        self.assertEqual(self.partner, confirm_msg.notified_partner_ids)
        self.assertEqual(
            [c1.name, c2.name], self._get_contract_names_from_mail(confirm_msg)
        )

    def test_sponsor_confirmation_email_cancelled_early(self):
        "If a new contract with a sponsor code is cancelled early, no notification mail should be sent"
        self._reserve_coupon_and_confirm(self.so)

        new_contract = self.env["contract.contract"].of_sale(self.so)
        new_contract.date_start = "2026-03-01"
        new_contract.date_end = "2026-03-10"

        self._trigger_sponsor_msg_cron()
        self.assertFalse(self.partner.message_ids)
