from datetime import date, timedelta
import traceback as tb

from lxml import html, etree

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server

from odoo.tests.common import HttpCase, at_install, post_install


def value2int(lxml_element):
    return int(lxml_element.get("value"))


def ts_link_names(doc, strip="/page/self-troubleshoot-"):
    hrefs = doc.xpath("//a[starts-with(@href, '%s')]/@href" % strip)
    return set(href[len(strip):] for href in hrefs)


def is_ts_page_ref(ref_instance):
    ref = ref_instance.env.ref
    doc = etree.fromstring(ref(ref_instance.complete_name).arch)
    return bool(doc.xpath("//form"))


@at_install(False)
@post_install(True)
class PagesTC(HttpCase):

    def setUp(self):
        super(PagesTC, self).setUp()
        self.werkzeug_environ = {'REMOTE_ADDR': '127.0.0.1'}
        self.test_client = Client(wsgi_server.application, BaseResponse)
        self.password = u'portal'
        self.user = self.env.ref("portal.demo_user0")
        self.dbname = self.env.cr.dbname
        self._login()

    def _create_ct(self, name):
        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            return env["account.analytic.contract"].create({
                "name": name,
            })

    def _login(self):
        "Authenticate the test client with the `self.user` portal user"
        doc = self.get_page('/web/login/', data={'db': self.dbname})
        csrf_token = doc.xpath("//input[@name='csrf_token']")[0].get('value')
        data = {
            'login': self.user.login,
            'password': self.password,
            'csrf_token': csrf_token,
            'db': self.dbname,
            'redirect': '/my/home',
        }
        response = self.test_client.post(
            '/web/login/', data=data, environ_base=self.werkzeug_environ)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/home", response.data)

    def get_page(self, path, data=None):
        "Return an lxml doc obtained from the html at given url path"
        response = self.test_client.get(
            path, query_string=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200, path)
        return html.fromstring(response.data)

    def create_contract(self, template, ended=False, in_commitment=True, **kw):
        attrs = {
            "name": u"Test contract",
            "recurring_invoices": True,
            "contract_template_id": template and template.id,
            "date_start": "2020-01-01",
            "partner_id": self.user.partner_id.id,
        }
        if ended:
            attrs["date_end"] = "2022-01-01"
        if in_commitment:
            attrs["min_contract_end_date"] = (
                date.today() + timedelta(days=80)).isoformat()
        else:
            attrs["min_contract_end_date"] = attrs["date_start"]

        attrs.update(kw)

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            return env["account.analytic.account"].create(attrs)

    def _ts_page_ids(self, *args):
        """ Return the trouble shooting wizard page xmlids (w/o the module part)
        which name match the given search words.
        """
        ids = set()
        for arg in args:
            ids |= set(self.env["ir.model.data"].search([
                ("model", "=", "ir.ui.view"),
                ("module", "=", "commown_self_troubleshooting"),
                ("name", "=like", arg + "%"),
            ]).filtered(is_ts_page_ref).mapped("name"))
        return ids

    def _contract_options(self, doc, apply_transform=None):
        "Find and return the contract id options found in given page html doc"
        xpath = "//div[@id='step-0']//select[@id='device_contract']//option"
        apply_transform = apply_transform or (lambda o: o)
        return set(apply_transform(o) for o in doc.xpath(xpath)
                   if o.get("disabled", None) != "disabled")

    def _contract_name_like(self, page_name):
        """ Find and return the contract_name_like variable value from the qweb
        arch of given self troubleshooting page xmlid (without the module part).
        """
        tmpl = self.env.ref("commown_self_troubleshooting.%s" % page_name)
        return etree.fromstring(tmpl.arch).xpath(
            "//t[@t-set='contract_name_like']/text()")[0]

    def test_portal_no_contract(self):
        "Portal home must not crash if user has a no or not-templated contracts"
        doc = self.get_page('/my/home')
        self.assertFalse(ts_link_names(doc))
        self.create_contract(False)
        doc = self.get_page('/my/home')
        self.assertFalse(ts_link_names(doc))

    def test_portal_with_contracts(self):
        "Page should load without crashing if user has a no template-contract"
        self.create_contract(self._create_ct("FP2/B2C"))
        doc = self.get_page('/my/home')
        self.assertEquals(ts_link_names(doc), self._ts_page_ids('fp2'))
        self.create_contract(self._create_ct("FP3+/B2B"))
        doc = self.get_page('/my/home')
        self.assertEquals(ts_link_names(doc), self._ts_page_ids('fp2', 'fp3'))

    def test_page_contract_options(self):
        ct = self._create_ct("FP2/B2C")
        future_date = (date.today() + timedelta(days=60)).isoformat()

        c1 = self.create_contract(ct)
        c2 = self.create_contract(ct)
        self.create_contract(ct, ended=True)
        c4 = self.create_contract(ct, in_commitment=False)
        c5 = self.create_contract(ct, date_end=future_date)

        doc = self.get_page('/page/self-troubleshoot-fp2-battery')
        self.assertEquals(self._contract_options(doc, value2int),
                          set((c1 | c2 | c4 | c5).ids))

    def test_pages_load_without_errors(self):
        "All pages should be generated without an error"

        # We create a contract to appear on each page, to check the contract
        # choice selector does not crash
        contract_created = {}

        for page_name in sorted(self._ts_page_ids("")):
            ct_name =  self._contract_name_like(page_name) + "/B2C"

            if ct_name not in contract_created:
                contract_created[ct_name] = self.create_contract(
                    self._create_ct(ct_name))

            try:
                doc = self.get_page('/page/self-troubleshoot-%s' % page_name)
            except Exception as exc:
                self.fail("Error loading %s:\n%s"
                          % (page_name, tb.format_exc(exc)))

            self.assertEqual(
                self._contract_options(doc, value2int),
                {contract_created[ct_name].id},
                "Wrong contract choice list in page '%s'" % page_name)
