import traceback as tb
from datetime import date, timedelta

from lxml import html
from mock import patch
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase

from ..models.res_partner import ResPartner


def value2int(lxml_element):
    return int(lxml_element.get("value"))


def ts_link_urls(doc):
    return set(doc.xpath("//a[starts-with(@href, '/page/self-troubleshoot-')]/@href"))


class PagesTC(HttpCase):
    def setUp(self):
        super(PagesTC, self).setUp()
        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        self.test_client = Client(wsgi_server.application, BaseResponse)
        self.password = b"portal"
        self.user = self.env.ref("base.demo_user0")
        self.dbname = self.env.cr.dbname
        self._login()
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            self.product_id = (
                env["product.product"]
                .create({"name": "Test service product", "type": "service"})
                .id
            )

    def _create_ct(self, name):
        with self.registry.cursor() as test_cursor:
            return self.env(test_cursor)["contract.template"].create({"name": name})

    def _login(self):
        "Authenticate the test client with the `self.user` portal user"
        doc = self.get_page("/web/login/", data={"db": self.dbname})
        csrf_token = doc.xpath("//input[@name='csrf_token']")[0].get("value")
        data = {
            "login": self.user.login,
            "password": self.password,
            "csrf_token": csrf_token,
            "db": self.dbname,
            "redirect": "/my/home",
        }
        response = self.test_client.post(
            "/web/login/", data=data, environ_base=self.werkzeug_environ
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/home", str(response.data))

    def get_page(self, path, data=None):
        "Return an lxml doc obtained from the html at given url path"
        response = self.test_client.get(path, query_string=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200, path)
        return html.fromstring(response.data)

    def create_contract(self, template, ended=False, in_commitment=True, **kw):
        date_start = "2020-01-01"
        cline_attrs = {
            "name": "Line 1",
            "specific_price": 1.0,
            "quantity": 1.0,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "product_id": self.product_id,
            "date_start": date_start,
        }
        if ended:
            cline_attrs["date_end"] = "2022-01-01"
        attrs = {
            "name": "Test contract",
            "contract_template_id": template and template.id,
            "partner_id": self.user.partner_id.id,
            "contract_line_ids": [(0, 0, cline_attrs)],
        }
        if in_commitment:
            attrs["commitment_end_date"] = (
                date.today() + timedelta(days=80)
            ).isoformat()
        else:
            attrs["commitment_end_date"] = date_start

        attrs.update(kw)

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            contract = env["contract.contract"].create(attrs)
            contract._compute_date_end()  # compute start date
            return contract

    def _ts_page_urls(self, *args):
        """Return the trouble shooting wizard page xmlids (w/o the module part)
        which name match the given search words.
        """
        urls = set()
        for arg in args:
            page_ids = (
                self.env["ir.model.data"]
                .search(
                    [
                        ("model", "=", "website.page"),
                        ("module", "=", "commown_self_troubleshooting"),
                        ("name", "=like", arg + "%"),
                    ]
                )
                .mapped("res_id")
            )
            urls |= set(self.env["website.page"].browse(page_ids).mapped("url"))
        return urls

    def _contract_options(self, doc, apply_transform=None):
        "Find and return the contract id options found in given page html doc"
        xpath = "//div[@id='step-0']//select[@id='device_contract']//option"
        apply_transform = apply_transform or (lambda o: o)
        return {
            apply_transform(o)
            for o in doc.xpath(xpath)
            if o.get("disabled", None) != "disabled"
        }

    def test_portal_no_contract(self):
        "Portal home must not crash if user has no or a not-templated contract"
        doc = self.get_page("/my/home")
        self.assertFalse(ts_link_urls(doc))

        # Do not test for absence of troubleshooting links when there
        # is a contract, as there will be one at least, to terminate it
        self.create_contract(False)
        self.get_page("/my/home")

    def test_portal_with_contracts(self):
        "Page should load without crashing if user has a no template-contract"
        self.create_contract(self._create_ct("FP2/B2C"))
        doc = self.get_page("/my/home")
        self.assertGreater(ts_link_urls(doc), self._ts_page_urls("fp2"))
        self.create_contract(self._create_ct("FP3+/B2B"))
        doc = self.get_page("/my/home")
        self.assertGreater(ts_link_urls(doc), self._ts_page_urls("fp2", "fp3"))

    def test_page_contract_options(self):
        ct = self._create_ct("FP2/B2C")
        future_date = (date.today() + timedelta(days=60)).isoformat()

        c1 = self.create_contract(ct)
        c2 = self.create_contract(ct)
        self.create_contract(ct, ended=True)
        c4 = self.create_contract(ct, in_commitment=False)
        c5 = self.create_contract(ct, date_end=future_date)

        doc = self.get_page("/page/self-troubleshoot-fp2-battery")
        self.assertEquals(
            self._contract_options(doc, value2int), set((c1 | c2 | c4 | c5).ids)
        )

    def test_pages_load_without_errors(self):
        """All pages should be generated without an error

        res.partner's method `self_troubleshooting_contracts` is mocked here as
        it is tested elsewhere.
        """

        cid = self.create_contract(self._create_ct("no-matter-name")).id

        with self.registry.cursor() as test_cursor:
            contract = self.env(test_cursor)["contract.contract"].browse(cid)

            for page_url in sorted(self._ts_page_urls("")):

                try:
                    with patch.object(
                        ResPartner,
                        "self_troubleshooting_contracts",
                        return_value=contract,
                    ) as m:
                        doc = self.get_page(page_url)
                except:
                    self.fail("Error loading %s:\n%s" % (page_url, tb.format_exc()))

                self.assertEqual(
                    self._contract_options(doc, value2int),
                    {cid},
                    "Wrong contract choice list in page '%s'" % page_url,
                )
