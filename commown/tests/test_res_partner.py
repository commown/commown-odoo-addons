from pathlib import Path
from urllib.parse import urlencode

from lxml import html

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase, get_db_name, HOST, PORT


HERE = (Path(__file__) / "..").resolve()


def _csrf_token(page):
    return page.xpath("string(//input[@name='csrf_token']/@value)")


class ResPartnerResetPasswordTC(HttpCase):

    def setUp(self):
        super(ResPartnerResetPasswordTC, self).setUp()
        self.partner = self.env.ref('base.partner_demo_portal')
        self.partner.signup_prepare()
        self.env.cr.commit()

    def get_page(self, test_client, path, **data):
        "Return an lxml doc obtained from the html at given url path"
        response = test_client.get(
            path, query_string=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200, path)
        return html.fromstring(response.data)

    def get_form(self, test_client, path, **data):
        "Get given page and return a name: value dict of its inputs and selects"
        page = self.get_page(test_client, path, **data)
        form = {n.get('name'): n.get('value') for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath(
                'string(option[@selected]/@value)')
        return form

    def test_reset_password(self):
        token = self.partner.signup_token
        # Fetch reset password form
        res = self.url_open('/web/reset_password?token=%s' % token)
        self.assertEqual(200, res.status_code)
        # Check that firstname and lastname are present and correctly valued
        doc = html.fromstring(res.text)
        self.assertEqual([self.partner.lastname],
                         doc.xpath('//input[@name="lastname"]/@value'))
        self.assertEqual([self.partner.firstname],
                         doc.xpath('//input[@name="firstname"]/@value'))
        self.assertEqual(['portal'],
                         doc.xpath('//input[@name="login"]/@value'))
        # Reset the password
        data = {'login': 'portal',
                'password': 'dummy_pass',
                'confirm_password': 'dummy_pass',
                'csrf_token': _csrf_token(doc)}
        url = "http://%s:%s/web/reset_password?token=%s" % (HOST, PORT, token)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = self.opener.post(url, data=urlencode(data), headers=headers)
        self.assertEqual(200, res.status_code)
        # Test authentication with the new password
        self.assertTrue(self.registry['res.users'].authenticate(
            get_db_name(), 'portal', 'dummy_pass', None))

    def test_documents(self):
        """ Portal users must be able to post their documents
        ... and see the upload state on their home page
        """

        # Prepare test: login and get account page:
        user = self.partner.user_ids.ensure_one()
        werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        test_client = Client(wsgi_server.application, BaseResponse)

        login_form = self.get_form(test_client, "/web/login/", db=get_db_name())
        login_form.update({
            "login": user.login,
            "password": "portal",
            "redirect": "/my/account",
        })
        response = test_client.post(
            "/web/login/", data=login_form, environ_base=werkzeug_environ)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/account", str(response.data))

        # Post id_card1
        account_form = self.get_form(test_client, "/my/account")

        with open(HERE / "smallest.pdf", "rb") as fobj:
            account_form.update({
                "redirect": "/my/home",
                "id_card1": (fobj, "card1.pdf"),
                "id_card2": "",
                "proof_of_address": "",
            })
            response = test_client.post(
                "/my/account", data=account_form, environ_base=werkzeug_environ)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/my/home", response.data.decode("utf-8"))

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            partner = env["res.partner"].browse(self.partner.id)
            self.assertTrue(partner.id_card1)
