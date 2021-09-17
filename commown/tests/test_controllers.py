import requests
from xmlrpc.client import ServerProxy

from odoo.tests.common import HttpCase, at_install, post_install, HOST, PORT
from odoo import tools

from .common import MockedEmptySessionMixin


BASE_URL = 'http://%s:%s' % (HOST, PORT)


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

        old_nb_reqs = self._nb_affiliate_requests()

        aff = self.env['sale.affiliate'].search([])[0]
        resp = requests.get(
            BASE_URL + '/shop/redirect?aff_ref=%s&redirect=/test/a' % aff.id,
            headers={'Cookie': 'session_id=%s' % self.session_id})

        self.assertTrue(resp.history and resp.history[0].is_redirect)
        self.assertEqual(resp.history[0].headers['Location'],
                         BASE_URL + '/test/a')
        self.assertEqual(self._nb_affiliate_requests(), old_nb_reqs + 1)

    def _nb_affiliate_requests(self):
        db, passwd = tools.config['db_name'], tools.config['admin_passwd']
        server = ServerProxy(BASE_URL + '/xmlrpc/2/common')
        uid = server.authenticate(db, 'admin', passwd, {})
        return ServerProxy(BASE_URL + '/xmlrpc/2/object').execute_kw(
            db, uid, passwd, 'sale.affiliate.request', 'search_count', [[], []])

    def test_shop_redirect_ok(self):
        self.check_redirect('aff_ref=1&redirect=/test/a', '/test/a')

    def test_shop_redirect_spam(self):
        self.check_redirect('redirect=https://mystupidsite.com', '/shop')
