import requests

from odoo.tests.common import HttpCase, at_install, post_install, HOST, PORT

from .common import MockedEmptySessionMixin


@at_install(False)
@post_install(True)
class ControllerTC(MockedEmptySessionMixin, HttpCase):

    def check_redirect(self, path, expected_path):
        # Required by the affiliate request creation
        self.request_mock.httprequest.headers.environ = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test',
            'HTTP_ACCEPT_LANGUAGE': 'fr',
        }

        url = 'http://%s:%s' % (HOST, PORT)
        resp = requests.get(
            url + '/shop/redirect?' + path,
            headers={'Cookie': 'session_id=%s' % self.session_id})

        self.assertTrue(resp.history and resp.history[0].is_redirect)
        self.assertEqual(resp.history[0].headers['Location'],
                         url + expected_path)

    def test_shop_redirect_ok(self):
        self.check_redirect('aff_ref=1&redirect=/test/a', '/test/a')

    def test_shop_redirect_spam(self):
        self.check_redirect('redirect=https://mystupidsite.com', '/shop')
