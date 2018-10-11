from mock import patch

from odoo.tests.common import TransactionCase


class MockedEmptySessionTC(TransactionCase):

    def setUp(self):
        super(MockedEmptySessionTC, self).setUp()

        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={})
        self.fake_session = request_mock.session
        self.addCleanup(request_patcher.stop)
