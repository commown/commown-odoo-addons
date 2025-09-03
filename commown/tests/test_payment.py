from datetime import datetime
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account_payment_slimpay.tests.common import MockedSlimpayMixin
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC

from .common import fake_slimpay_server_env_config


@tagged("-at_install", "post_install")
class PaymentTC(MockedSlimpayMixin, RentalSaleOrderTC):
    def setUp(self):
        request_patcher = patch(
            "odoo.addons.website_sale_affiliate"
            ".models.sale_affiliate_request.AffiliateRequest"
        )
        request_mock = request_patcher.start()
        request_mock.configure_mock(session={})
        self.fake_session = request_mock.session

        super().setUp()
        self.so = self.create_sale_order()

        self.setup_mocks()
        self.addCleanup(request_patcher.stop)

    @fake_slimpay_server_env_config()
    def test_token_replaced(self):
        "Partner payment_token_id must be the last token created for a web sale"
        # Assign an "old" token to the web partner:
        self.slimpay.journal_id = (
            self.env["account.journal"].search([("type", "=", "bank")], limit=1).id
        )
        partner = self.so.partner_id
        old_token = self.env["payment.token"].create(
            {
                "payment_details": "Test Token",
                "partner_id": partner.id,
                "active": True,
                "provider_id": self.slimpay.id,
                "provider_ref": "mandate_old",
            }
        )
        partner.payment_token_id = old_token.id

        # Simulate a website sale:
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": self.slimpay.id,
                "amount": self.so.amount_total,
                "currency_id": self.so.pricelist_id.currency_id.id,
                "partner_id": partner.id,
                "partner_country_id": partner.country_id.id,
                "reference": self.so.name,
                "sale_order_ids": [Command.set([self.so.id])],
            }
        )
        self.fake_get.return_value = {
            "reference": tx.reference,
            "state": "closed.completed",
            "id": "test-id",
            "dateClosed": datetime.today().isoformat(),
        }
        self.slimpay._slimpay_s2s_validate(
            tx, {"reference": tx.reference, "_links": {"self": {"href": "fake_url"}}}
        )

        # Check that partner's token changed and is the one associated
        # to the transaction:
        self.assertNotEqual(partner.payment_token_id, old_token)
        self.assertEqual(partner.payment_token_id, tx.payment_token_id)
