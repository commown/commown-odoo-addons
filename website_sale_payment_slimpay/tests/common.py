from datetime import datetime
from json import dumps as json_dumps

import lxml.html
from mock import patch

import odoo.http
from odoo.tests.common import HttpCase, tagged

from odoo.addons.account_payment_slimpay.models.slimpay_utils import SlimpayClient


def tag_data(lxml_tag, **types):
    "Helper to mimic javascript tag.data() result on a lxml tag"
    result = {}
    for key, val in lxml_tag.items():
        if key.startswith("data-"):
            new_key = key[5:].replace("-", "_")
            result[new_key] = types.get(new_key, str)(val)
    return result


def _get_from_doc_mock(doc, method_name):
    """Dummy mock for SimplayClient.get_from_doc that returns a hard-coded
    hal document for the requested method name, whatever the specified doc.
    """
    return {
        "get-mandate": {"id": "my-mandate-id"},
        "get-bank-account": {"institutionName": "my-bank", "iban": "my-iban"},
    }[method_name]


@tagged("-at_install", "post_install")
class SlimpayControllersTC(HttpCase):
    timeout = 12  # Use much bigger values for interactive debugging

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

    def setUp(self):
        self._patchers = []
        # Mock SlimpayClient
        self._start_patcher(
            patch("odoo.addons.account_payment_slimpay.models.slimpay_utils.get_client")
        )
        # Mock its "get" and "get_from_doc" methods (to ease their config)
        self.fake_get = self._start_patcher(patch.object(SlimpayClient, "get"))
        self._start_patcher(
            patch.object(SlimpayClient, "get_from_doc", side_effect=_get_from_doc_mock)
        )

        def fake_approval(tx_ref, *args, **kw):
            return f"https://slimpay.test/hello?code=mycode&tx_ref={tx_ref}"

        # Mock approval_url
        self._start_patcher(
            patch.object(SlimpayClient, "approval_url", side_effect=fake_approval)
        )

        super().setUp()
        # Stop patchers in case of a test exception or normal termination
        for patcher in self._patchers:
            self.addCleanup(patcher.stop)

        # Setup Slimpay provider
        self.slimpay = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        self.slimpay.update(
            {
                "state": "enabled",
                "is_published": True,
                "allow_express_checkout": True,
                "maximum_amount": False,
            }
        )
        self.env["account.payment.method"].create(
            {"code": "slimpay", "name": "Slimpay", "payment_type": "inbound"}
        )
        journal = (
            self.env["account.journal"]
            .search(
                [("type", "=", "bank"), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            .ensure_one()
        )
        self.slimpay.journal_id = journal.id

        # Do not send invoice confirmation email:
        self.env.ref("sale.mail_template_sale_confirmation").unlink()

        # Automatically create invoice on sale confirmation:
        self.env["ir.config_parameter"].sudo().set_param("sale.automatic_invoice", True)

    def _start_patcher(self, patcher):
        self._patchers.append(patcher)
        return patcher.start()

    def post(self, url, data=None, json=None, headers=None, assert_code=200):
        """POST an http request using requests. Complements HttpCase.url_open
        with headers and json"""
        if url.startswith("/"):  # pragma: no cover
            url = self.base_url() + url
        resp = self.opener.post(
            url, data=data, json=json, timeout=self.timeout, headers=headers
        )
        self.assertEqual(assert_code, resp.status_code)
        return resp.text if json is None else resp.json()

    def jsonrpc(self, path, params=None, assert_code=200):
        "Helper method to perform a jsonrpc request and return its result"
        headers = {"Content-Type": "application/json"}
        data = {"jsonrpc": "2.0", "method": "call", "params": params or {}}
        json = self.post(path, json=data, headers=headers, assert_code=assert_code)
        try:
            return json["result"]
        except KeyError:  # pragma: no cover
            self.fail("jsonrpc error:\n%s" % json)

    def search_read(self, model, *args, kwargs=None):
        "Helper method to perform a model + domain search via jsonrpc"
        return self.jsonrpc(
            "/web/dataset/call_kw",
            {
                "model": model,
                "method": "search_read",
                "args": args,
                "kwargs": kwargs or {},
            },
        )

    def csrf_token(self, html_text):
        doc = lxml.html.fromstring(html_text)
        return doc.xpath("//input[@name='csrf_token']")[0].get("value")

    def add_product_to_user_cart(self):
        product = self.env.ref("product.product_delivery_02_product_template")
        csrf_token = self.csrf_token(
            self.url_open(product.website_url, timeout=self.timeout).text
        )
        self.post(
            "/shop/cart/update",
            data={
                "product_id": product.product_variant_id.id,
                "csrf_token": csrf_token,
            },
        )
        csrf_token = self.csrf_token(
            self.url_open("/shop/checkout", timeout=self.timeout).text
        )
        self.post("/shop/confirm_order", data={"csrf_token": csrf_token})

    def pay_cart(self, **params):
        """Simulate a click on Slimpay "Pay" button.
        `SlimpayClient.approval_url` mock returns the transaction
        reference instead of a Slimpay URL, so we can use it later to
        check the transaction.
        """
        page = self.url_open("/shop/payment", timeout=self.timeout)
        doc = lxml.html.fromstring(page.text)
        form = doc.xpath("//form[@name='o_payment_checkout']")[0]
        radio = doc.xpath(".//input[@name='o_payment_radio' and @checked='True']")[0]

        types = dict(
            amount=float,
            currency_id=int,
            payment_option_id=int,
            partner_id=int,
            allow_token_selection=bool,
        )
        params = tag_data(form, **types)
        params.update(tag_data(radio, **types))
        params.update(flow="redirect", tokenization_requested=False)

        # Re-read session as it was completed server-side
        so_id = odoo.http.root.session_store.get(self.session.sid)["sale_order_id"]
        tx_data = self.jsonrpc("/shop/payment/transaction/%d" % so_id, params=params)

        form = lxml.html.fromstring(tx_data["redirect_form_html"])
        self.assertEqual(form.get("action"), "https://slimpay.test/hello")
        params = dict(form.form_values())
        self.assertEqual(params, {"code": "mycode", "tx_ref": tx_data["reference"]})
        return tx_data["reference"]

    def simulate_feedback(self, tx_ref, state="closed.completed", assert_code=200):
        """Simulate a (by default OK) Slimpay feedback.
        Requires mocks for SlimpayClient.get and SlimpayClient.get_from_doc.
        """
        feedback = {
            "reference": tx_ref,
            "_links": {"self": {"href": "http://slimpay_order_url"}},
        }
        self.fake_get.return_value = {
            "reference": tx_ref,
            "state": state,
            "id": "test-id",
            "dateClosed": datetime.today().isoformat(),
        }
        return self.post(
            "/payment/slimpay/s2s/feedback",
            data=json_dumps(feedback),
            headers={"Content-Type": "application/hal+json"},
            assert_code=assert_code,
        )

    def check_transaction(self, tx_ref, state):
        tx = self.search_read("payment.transaction", [("reference", "=", tx_ref)])[0]
        self.assertEqual(state, tx["state"])
        self.assertEqual([self.slimpay.id, self.slimpay.name], tx["provider_id"])
        return tx

    def check_so(self, so_id, state):
        so = self.search_read("sale.order", [("id", "=", so_id)], ["state"])
        self.assertEqual([{"id": so_id, "state": state}], so)
