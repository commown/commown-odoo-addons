from urllib.parse import urlencode

from lxml import html

from odoo.tests.common import HttpCase, get_db_name, HOST, PORT
from odoo.addons.product_rental.tests.common import (
    RentalSaleOrderMixin, MockedEmptySessionMixin)


def _csrf_token(page):
    return page.xpath("string(//input[@name='csrf_token']/@value)")


class ResPartnerResetPasswordTC(RentalSaleOrderMixin,
                                MockedEmptySessionMixin,
                                HttpCase):

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
