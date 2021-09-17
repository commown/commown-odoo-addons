import lxml.html

from odoo.tests.common import HttpCase, at_install, post_install, get_db_name


@at_install(False)
@post_install(True)
class ResPartnerResetPasswordTC(HttpCase):

    def test_reset_password(self):
        self.partner = self.env.ref('base.partner_demo_portal')
        self.partner.signup_prepare()
        token = self.partner.signup_token

        # Fetch reset password form
        res = self.url_open('/web/reset_password?token=%s' % token)
        self.assertEqual(200, res.status_code)
        # Check that firstname and lastname are present and correctly valued
        html = res.text
        doc = lxml.html.fromstring(html)
        self.assertEqual(['Willis'],
                         doc.xpath('//input[@name="lastname"]/@value'))
        self.assertEqual(['Joel'],
                         doc.xpath('//input[@name="firstname"]/@value'))

        # Reset the password
        csrf_token = doc.xpath('//input[@name="csrf_token"]/@value')[0]
        data = {'login': 'portal',
                'password': 'dummy_pass',
                'confirm_password': 'dummy_pass',
                'csrf_token': csrf_token}
        res = self.url_open('/web/reset_password?token=%s' % token, data=data)
        # Test authentication with the new password
        self.assertTrue(self.registry['res.users'].authenticate(
            get_db_name(), 'portal', 'dummy_pass', None))
