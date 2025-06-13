import datetime

from lxml.etree import tostring

from .common import ReportTC


class SaleOrderReportTC(ReportTC):
    report_name = "sale.report_saleorder"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so = cls.env.ref("sale.sale_order_1")
        assert cls.so.state == "draft", "Test pre-requisite failure"

    def test_sale_order_actions(self):
        view = self.env.ref("sale.view_order_form")
        result = self.env["sale.order"].get_views(
            [(view.id, "form")], {"toolbar": True}
        )

        print_actions = sorted(
            [a["name"] for a in result["views"]["form"]["toolbar"].get("print", [])]
        )

        self.assertIn(
            "[commown] Print sale order",
            print_actions,
        )

    def test_title_state_draft(self):
        doc = self.html_report(self.so)

        so_date = self.so.date_order.strftime("%m/%d/%Y")  # US style
        self.assertEqual(
            self.h1(doc),
            "Quotation %s - %s" % (self.so.display_name, so_date),
        )

    def test_title_state_sale(self):
        self.so.action_confirm()
        assert self.so.state == "sale", "Pre-requisite failure"

        doc = self.html_report(self.so)
        conf_date = self.so.date_order.strftime("%m/%d/%Y")  # US style
        self.assertEqual(
            self.h1(doc),
            "Order Acknowledgement %s - %s" % (self.so.display_name, conf_date),
        )

    def test_client_order_ref_false(self):
        self.so.client_order_ref = False
        self.assertFalse(b"Your reference" in tostring(self.html_report(self.so)))

    def test_client_order_ref_true(self):
        self.so.client_order_ref = "TEST-REF"
        html = tostring(self.html_report(self.so))
        self.assertTrue(b"Your reference" in html)
        self.assertTrue(b"TEST-REF" in html)

    def test_payment_term_false(self):
        self.so.payment_term_id = False
        self.assertFalse(b"Payment conditions" in tostring(self.html_report(self.so)))

    def test_payment_term_true_validity_date_false(self):
        ref = self.env.ref
        self.so.payment_term_id = ref("account.account_payment_term_immediate").id
        self.so.validity_date = False
        html = tostring(self.html_report(self.so))
        self.assertTrue(b"Payment conditions" in html)
        self.assertTrue(b"Payment terms: Immediate" in html)
        self.assertFalse(b"good for agreement" in html)

    def test_payment_term_true_validity_date_true(self):
        ref = self.env.ref
        self.so.payment_term_id = ref("account.account_payment_term_immediate").id
        self.so.validity_date = datetime.date(2040, 12, 31)
        html = tostring(self.html_report(self.so))
        self.assertTrue(b"Payment conditions" in html)
        self.assertTrue(b"Payment terms: Immediate" in html)
        self.assertTrue(b"good for agreement" in html)
        self.assertTrue(b"12/31/2040" in html)

    def test_order_note(self):
        self.so.note = "Sale order test note"
        html = tostring(self.html_report(self.so))
        self.assertTrue(b"Notes" in html)
        self.assertTrue(b"Sale order test note" in html)
