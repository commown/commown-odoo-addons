from urllib import urlencode

import lxml.html

from odoo.tests.common import HttpCase, at_install, post_install, get_db_name


@at_install(False)
@post_install(True)
class ResPartnerTC(HttpCase):

    def setUp(self):
        super(ResPartnerTC, self).setUp()
        partner = self.env['res.partner'].search(
            [('user_ids.login', '=', 'portal')])
        partner.signup_prepare()
        self.env.cr.commit()
        self.token = partner.signup_token

    def test_reset_password(self):
        # Fetch reset password form
        res = self.url_open('/web/reset_password?token=%s' % self.token)
        self.assertEqual(200, res.code)
        # Check that firstname and lastname are present and correctly valued
        html = res.read()
        with open('/tmp/toto.html', 'w') as fobj:
            fobj.write(html)
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
            '/web/reset_password?token=%s' % self.token,
            data=urlencode(data))
        # Test authentication with the new password
        self.assertTrue(self.registry['res.users'].authenticate(
            get_db_name(), 'portal', 'dummy_pass', None))
