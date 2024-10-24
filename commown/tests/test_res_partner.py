import datetime
from urllib.parse import urlencode

from lxml import html

from odoo.tests.common import HOST, PORT, HttpCase, SavepointCase, get_db_name

from odoo.addons.product_rental.tests.common import (
    MockedEmptySessionMixin,
    RentalSaleOrderMixin,
)

from .common import ContractRelatedPaymentTokenUniquifyTC


def _csrf_token(page):
    return page.xpath("string(//input[@name='csrf_token']/@value)")


_pay_prefs1 = {
    "invoice_merge_next_date": datetime.date(2020, 1, 1),
    "invoice_merge_recurring_rule_type": "yearly",
    "invoice_merge_recurring_interval": 1,
}

_pay_prefs2 = {
    "invoice_merge_next_date": datetime.date(2023, 2, 2),
    "invoice_merge_recurring_rule_type": "monthly",
    "invoice_merge_recurring_interval": 3,
}


class ResPartnerResetPasswordTC(
    RentalSaleOrderMixin, MockedEmptySessionMixin, HttpCase
):
    def setUp(self):
        super(ResPartnerResetPasswordTC, self).setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        self.partner.signup_prepare()
        self.env.cr.commit()

    def get_page(self, test_client, path, **data):
        "Return an lxml doc obtained from the html at given url path"
        response = test_client.get(path, query_string=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200, path)
        return html.fromstring(response.data)

    def get_form(self, test_client, path, **data):
        "Get given page and return a name: value dict of its inputs and selects"
        page = self.get_page(test_client, path, **data)
        form = {n.get("name"): n.get("value") for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath("string(option[@selected]/@value)")
        return form

    def test_reset_password(self):
        token = self.partner.signup_token
        # Fetch reset password form
        res = self.url_open("/web/reset_password?token=%s" % token)
        self.assertEqual(200, res.status_code)
        # Check that firstname and lastname are present and correctly valued
        doc = html.fromstring(res.text)
        self.assertEqual(
            [self.partner.lastname], doc.xpath('//input[@name="lastname"]/@value')
        )
        self.assertEqual(
            [self.partner.firstname], doc.xpath('//input[@name="firstname"]/@value')
        )
        self.assertEqual(["portal"], doc.xpath('//input[@name="login"]/@value'))
        # Reset the password
        data = {
            "login": "portal",
            "password": "dummy_pass",
            "confirm_password": "dummy_pass",
            "csrf_token": _csrf_token(doc),
        }
        url = "http://%s:%s/web/reset_password?token=%s" % (HOST, PORT, token)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = self.opener.post(url, data=urlencode(data), headers=headers)
        self.assertEqual(200, res.status_code)
        # Test authentication with the new password
        self.assertTrue(
            self.registry["res.users"].authenticate(
                get_db_name(), "portal", "dummy_pass", None
            )
        )


class ResPartnerSimpleTC(SavepointCase):
    def test_create_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "supplier": True})

        expected = "401-F-%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)

    def test_update_to_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "supplier": False})

        expected = "401-F-%d" % p1.id
        self.assertNotEqual(p1.property_account_payable_id.code, expected)

        p1.supplier = True
        self.assertEqual(p1.property_account_payable_id.code, expected)

    def test_create_supplier_add_child(self):
        p1 = self.env["res.partner"].create(
            {"name": "p1", "supplier": True, "is_company": True}
        )
        p2 = self.env["res.partner"].create({"name": "p2", "parent_id": p1.id})

        expected = "401-F-%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)
        self.assertEqual(p2.property_account_payable_id.code, expected)

    def test_create_child_supplier(self):
        p1 = self.env["res.partner"].create({"name": "p1", "is_company": True})
        p2 = self.env["res.partner"].create({"name": "p2", "parent_id": p1.id})
        p3 = self.env["res.partner"].create({"name": "p3", "parent_id": p1.id})

        p3.supplier = True

        expected = "401-F-%d" % p1.id
        self.assertEqual(p1.property_account_payable_id.code, expected)
        self.assertEqual(p2.property_account_payable_id.code, expected)
        self.assertEqual(p3.property_account_payable_id.code, expected)

    def test_create_company_set_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test partner", "customer": True, "company_name": "Test company"},
        )

        partner._create_receivable_account()
        recv_acc = partner.property_account_receivable_id
        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, recv_acc)
        self.assertEqual(recv_acc.name, "Test company")
        self.assertEqual(recv_acc.code, "411-C-%d" % company.id)

    def test_create_company_with_custom_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test partner", "customer": True, "company_name": "Test company"},
        )

        partner._create_receivable_account()
        recv_acc = partner.property_account_receivable_id
        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, recv_acc)
        self.assertEqual(recv_acc.name, "Test company")
        self.assertEqual(recv_acc.code, "411-C-%d" % company.id)

    def test_create_company_without_custom_receivable_account(self):
        partner = self.env["res.partner"].create(
            {"name": "Test partner", "customer": True, "company_name": "Test company"},
        )

        # Test prerequisite:
        ref_account = self.env.ref("l10n_fr.1_fr_pcg_recv")
        self.assertEqual(partner.property_account_receivable_id, ref_account)

        partner.create_company()

        company = partner.parent_id
        self.assertEqual(company.property_account_receivable_id, ref_account)
        self.assertEqual(ref_account.code, "411100")  # unchanged!

    def _new_token(self, name, partner):
        acquirer = self.env.ref("account_payment_slimpay.payment_acquirer_slimpay")
        return self.env["payment.token"].create(
            {
                "name": name,
                "acquirer_id": acquirer.id,
                "partner_id": partner.id,
                "acquirer_ref": name,
            }
        )

    def test_sync_payment_fields(self):
        p_model = self.env["res.partner"]

        p_contact = p_model.create({"name": "p", "type": "contact"})

        tok1 = self._new_token("tok1", p_contact)
        tok2 = self._new_token("tok2", p_contact)

        p_contact.update(dict(_pay_prefs1, payment_token_id=tok1.id))

        # Check sync on invoice partner creation
        p_inv = p_model.create({"parent_id": p_contact.id, "type": "invoice"})
        expected_prefs1 = dict(_pay_prefs1, payment_token_id=tok1)
        self.assertEqual(expected_prefs1, {f: p_inv[f] for f in expected_prefs1})

        # Check invoice partner sync on parent update
        p_contact.update(dict(_pay_prefs2, payment_token_id=tok2.id))
        expected_prefs2 = dict(_pay_prefs2, payment_token_id=tok2)
        self.assertEqual(expected_prefs2, {f: p_inv[f] for f in expected_prefs2})

        # Check parent sync on invoice partner update
        p_inv.update(dict(_pay_prefs1, payment_token_id=tok1.id))
        self.assertEqual(expected_prefs1, {f: p_contact[f] for f in expected_prefs1})


class ResPartnerInvoiceActionTC(ContractRelatedPaymentTokenUniquifyTC):
    def test_action(self):
        "Action must reattribute contracts and draft invoices"
        partner = self.company_s1_w1
        inv_partner = partner.copy({"type": "invoice", "parent_id": partner.id})
        draft_inv = self.contract1._recurring_create_invoice()

        inv_partner.action_set_as_invoice_recipient()

        self.assertEqual(self.contract1.invoice_partner_id, inv_partner)
        self.assertEqual(draft_inv.partner_id, inv_partner)
