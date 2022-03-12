import datetime

import lxml.html

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server

from odoo.tests.common import HttpCase, at_install, post_install


def ts_link_names(doc, strip="/page/self-troubleshoot-"):
    hrefs = doc.xpath("//a[starts-with(@href, '%s')]/@href" % strip)
    return set(href[len(strip):] for href in hrefs)


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
        return lxml.html.fromstring(response.data)

    def create_contract(self, template, ended=False, in_commitment=True):
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
                datetime.date.today() + datetime.timedelta(days=80)).isoformat()
        else:
            attrs["min_contract_end_date"] = attrs["date_start"]
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
            ]).mapped("name"))
        return ids

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
