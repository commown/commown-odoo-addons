from mock import patch

from odoo.tests.common import TransactionCase


class MockedEmptySessionMixin(object):

    def setUp(self):
        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        self.request_mock = request_patcher.start()
        self.request_mock.configure_mock(session={})
        self.fake_session = self.request_mock.session
        self.addCleanup(request_patcher.stop)

        super(MockedEmptySessionMixin, self).setUp()


class MockedEmptySessionTC(MockedEmptySessionMixin, TransactionCase):
    pass
