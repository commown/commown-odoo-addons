from urllib.parse import urlencode

import lxml.html

from odoo.tests.common import HttpCase, at_install, post_install, get_db_name


@at_install(False)
@post_install(True)
class ResPartnerResetPasswordTC(HttpCase):

    def setUp(self):
        super(ResPartnerResetPasswordTC, self).setUp()
        self.partner = self.env.ref('portal.demo_user0_res_partner')
        self.partner.signup_prepare()
        self.env.cr.commit()

    def test_reset_password(self):
        token = self.partner.signup_token
        # Fetch reset password form
        res = self.url_open('/web/reset_password?token=%s' % token)
        self.assertEqual(200, res.code)
        # Check that firstname and lastname are present and correctly valued
        html = res.read()
        doc = lxml.html.fromstring(html)
        self.assertEqual(['Demo'],
                         doc.xpath('//input[@name="lastname"]/@value'))
        self.assertEqual(['Portal User'],
                         doc.xpath('//input[@name="firstname"]/@value'))
        # Reset the password
        csrf_token = doc.xpath('//input[@name="csrf_token"]/@value')[0]
        data = {'login': 'portal',
                'password': 'dummy_pass',
                'confirm_password': 'dummy_pass',
                'csrf_token': csrf_token}
        res = self.url_open(
            '/web/reset_password?token=%s' % token,
            data=urlencode(data))
        # Test authentication with the new password
        self.assertTrue(self.registry['res.users'].authenticate(
            get_db_name(), 'portal', 'dummy_pass', None))
