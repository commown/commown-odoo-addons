import requests

from odoo.tests.common import HttpCase, at_install, post_install, HOST, PORT

from .common import MockedEmptySessionMixin


@at_install(False)
@post_install(True)
class ControllerTC(MockedEmptySessionMixin, HttpCase):

    def test_shop_redirect(self):
        # Required by the affiliate request creation
        self.request_mock.httprequest.headers.environ = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test',
            'HTTP_ACCEPT_LANGUAGE': 'fr',
        }

        aff = self.env['sale.affiliate'].search([])[0]
        url = 'http://%s:%s' % (HOST, PORT)
        resp = requests.get(
            url + '/shop/redirect?aff_ref=%s&redirect=/test/a' % aff.id,
            headers={'Cookie': 'session_id=%s' % self.session_id})

        self.assertTrue(resp.history and resp.history[0].is_redirect)
        self.assertEqual(resp.history[0].headers['Location'], url + '/test/a')
        self.assertEqual(len(aff.request_ids), 1)
