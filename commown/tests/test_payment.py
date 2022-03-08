from datetime import datetime

from mock import patch

from odoo.tests.common import at_install, post_install

from odoo.addons.account_payment_slimpay.tests.common import MockedSlimpayMixin
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@at_install(False)
@post_install(True)
class PaymentTC(MockedSlimpayMixin, RentalSaleOrderTC):

    def setUp(self):
        request_patcher = patch('odoo.addons.website_sale_affiliate'
                                '.models.sale_affiliate_request.request')
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={})
        self.fake_session = request_mock.session

        super(PaymentTC, self).setUp()
        self.so = self.create_sale_order()

        self.setup_mocks()
        self.addCleanup(request_patcher.stop)

    def test_token_replaced(self):
        "Partner payment_token_id must be the last token created for a web sale"
        # Assign an "old" token to the web partner:
        self.slimpay.journal_id = self.env["account.journal"].search([
            ("type", "=", "bank")], limit=1).id
        partner = self.so.partner_id
        old_token = self.env['payment.token'].create({
            'name': 'Test Token',
            'partner_id': partner.id,
            'active': True,
            'acquirer_id': self.slimpay.id,
            'acquirer_ref': 'mandate_old',
        })
        partner.payment_token_id = old_token.id

        # Simulate a website sale:
        tx = self.so._create_payment_transaction({
            'acquirer_id': self.slimpay.id,
            'type': 'form',
            'amount': self.so.amount_total,
            'currency_id': self.so.pricelist_id.currency_id.id,
            'partner_id': partner.id,
            'partner_country_id': partner.country_id.id,
            'reference': self.so.name,
        })
        self.fake_get.return_value = {
            'reference': tx.reference, 'state': 'closed.completed',
            'id': 'test-id', 'dateClosed': datetime.today().isoformat()}
        self.slimpay._slimpay_s2s_validate(tx, {
            'reference': tx.reference,
            '_links': {'self': {'href': 'fake_url'}}})

        # Check that partner's token changed and is the one associated
        # to the transaction:
        self.assertNotEqual(partner.payment_token_id, old_token)
        self.assertEqual(partner.payment_token_id, tx.payment_token_id)
