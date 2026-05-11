from pathlib import Path

import lxml.etree
import requests_mock

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.commown_shipping.tests.common import mock_colissimo_ok

HERE = (Path(__file__) / "..").resolve()


@tagged("-at_install", "post_install")
class TestRegistration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company.
            # (This is for the test_task_ok_payment test)
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

            cls.env.ref("urban_mine.product").property_account_expense_id = cls.env[
                "account.account"
            ].search(
                [
                    ("code", "=", "606800"),
                    ("company_id", "=", cls.env.company.id),
                ]
            )

        cls.fp3 = (
            cls.env["product.template"]
            .create({"name": "FP3", "purchase_ok": True})
            .product_variant_id
        )
        cls.project = cls.env.ref("urban_mine.project")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Elie A",
                "email": "elie@commown.fr",
                "street": "2 rue de Rome",
                "zip": "67000",
                "city": "Strasbourg",
                "country_id": cls.env.ref("base.fr").id,
                "supplier_rank": 1,
                "from_urban_mine": True,
            }
        )

    def get_tasks(self, partner_id):
        return self.env["project.task"].search(
            [
                ("project_id", "=", self.project.id),
                ("partner_id", "=", partner_id),
            ]
        )

    def get_last_note_message(self, task):
        return [
            m
            for m in task.message_ids
            if list(m.subtype_id.get_external_id().values()) == ["mail.mt_comment"]
        ][0]

    def check_coupon_message(self, task, campaign):
        "Check message title and the coupon included in the message"
        last_note_msg = self.get_last_note_message(task)
        self.assertIn("Accord de reprise", last_note_msg.subject)
        self.assertIn(task.urban_mine_name(), last_note_msg.subject)
        last_coupon = self.env["coupon.coupon"].search([], limit=1)
        self.assertIn(last_coupon.code, last_note_msg.body)
        self.assertEqual(
            last_coupon.campaign_id,
            self.env.ref("urban_mine." + campaign),
        )

    def test_task_creation(self):
        self.assertEqual(len(self.get_tasks(self.partner.id)), 1)

    def test_missing_storable_product(self):
        task = self.get_tasks(self.partner.id)
        task.storable_product_id = False
        with self.assertRaises(UserError) as err:
            task.update({"stage_id": self.env.ref("urban_mine.stage6")})
        self.assertEqual(
            err.exception.args[0],
            "Please fill-in the storable product field of the task!",
        )

    def test_task_ok_coupon_only(self):
        task = self.get_tasks(self.partner.id)
        # The line beneath changes the assigned user from the env. user.
        # (For coverage purposes)
        task.user_ids = self.env["res.users"].browse(2)

        task.storable_product_id = self.fp3.id
        task.update({"stage_id": self.env.ref("urban_mine.stage6")})
        self.check_coupon_message(task, "campaign_coupon_only")
        po = self.env["purchase.order"].search(
            [("partner_ref", "=", task.urban_mine_name())]
        )
        self.assertEqual(len(po), 1)
        self.assertEqual(po.partner_id, self.partner)
        self.assertEqual(po.state, "purchase")

    def test_task_ok_payment(self):
        ref = self.env.ref

        task = self.get_tasks(self.partner.id)
        task.storable_product_id = self.fp3.id
        task.project_id.company_id = ref("l10n_fr.demo_company_fr")
        task.company_id = ref("l10n_fr.demo_company_fr")
        task.company_id.partner_id.is_company = True

        with requests_mock.Mocker() as mocker:
            mock_colissimo_ok(mocker)
            task.update({"stage_id": ref("urban_mine.stage2")})

        # Check :
        # - the web service was called with the right parameters
        # - a return label was created and attached to the task
        # - the expedition reference is set on the task
        req = lxml.etree.fromstring(mocker.request_history[0].text.encode("utf-8"))
        std_account = ref("commown_shipping.carrier-account-colissimo-std-account")
        product = ref("urban_mine.product")

        self.assertEqual(req.xpath("//contractNumber/text()"), [std_account.account])
        self.assertEqual(req.xpath("//weight/text()"), [str(product.weight)])
        self.assertEqual(req.xpath("//sender//zipCode/text()"), ["67000"])
        self.assertEqual(req.xpath("//addressee//zipCode/text()"), ["35043"])

        self.assertTrue(task.message_ids)
        last_note_msg = self.get_last_note_message(task)
        self.assertIn("Accusé Réception", last_note_msg.subject)
        self.assertIn(task.urban_mine_name(), last_note_msg.subject)
        attachment = last_note_msg.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.mimetype, "application/pdf")

        # Next step: registration is validated
        # The invoice and coupon code must be sent by email

        # Use a fake auto-invoice report to avoid installing its dependencies
        report = ref("urban_mine.report_autoinvoice")
        report.py3o_template_fallback = "tests/fake_report.odt"

        # Launch test
        task.update({"stage_id": ref("urban_mine.stage4")})

        # Check results
        invoice = self.env["account.move"].search(
            [("payment_reference", "=", task.urban_mine_name())]
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(
            invoice.invoice_payment_term_id,
            ref("account.account_payment_term_15days"),
        )
        self.assertEqual(
            ref("urban_mine.product").product_variant_id,
            invoice.mapped("line_ids.product_id"),
        )
        self.assertEqual(
            invoice.amount_untaxed,
            ref("urban_mine.product").standard_price,
        )
        self.assertEqual(
            invoice.line_ids.mapped("analytic_tag_ids.name"),
            ["EXPL"],
        )
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", invoice._name),
                ("res_id", "=", invoice.id),
            ]
        )
        self.assertEqual(len(attachments), 1)
        self.check_coupon_message(task, "campaign_payment")

        po = self.env["purchase.order"].search(
            [("partner_ref", "=", task.urban_mine_name())]
        )
        self.assertEqual(len(po), 1)
        self.assertEqual(po.partner_ref, invoice.payment_reference)
        self.assertEqual(po.partner_id, self.partner)
        self.assertEqual(po.state, "purchase")
        self.assertEqual(po.invoice_ids, invoice)
        self.assertEqual(
            po.picking_type_id,
            ref("urban_mine.picking_type_receive_to_diagnose"),
        )
        self.assertEqual(invoice.invoice_origin, po.name)
