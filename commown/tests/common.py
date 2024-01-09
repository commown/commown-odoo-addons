import os
from contextlib import contextmanager

from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC
from odoo.addons.server_environment import server_env
from odoo.addons.server_environment.models import server_env_mixin


@contextmanager
def fake_slimpay_server_env_config(config=None):
    "Fake a server env config for slimpay acquirer using env variables"

    # Default config if not given
    if config is None:
        config = "\n".join(
            [
                "[payment_acquirer.Slimpay]",
                "slimpay_api_url=https://example.com",
                "slimpay_creditor=creditor",
                "slimpay_app_id=slimpay_app_id",
                "slimpay_app_secret=slimpay_app_secret",
            ]
        )

    # Save server environment state
    old_server_env_dir = server_env._dir
    old_server_env_config = server_env_mixin.serv_config
    old_env_server_env_config = os.environ.get("SERVER_ENV_CONFIG")

    try:
        # Execute the decorated function in the modified server environment
        server_env._dir = None
        os.environ["SERVER_ENV_CONFIG"] = config
        server_env_mixin.serv_config = server_env._load_config()
        yield
    finally:
        # Restore previous server environment state
        server_env._dir = old_server_env_dir
        server_env_mixin.serv_config = old_server_env_config
        if not old_env_server_env_config:
            del os.environ["SERVER_ENV_CONFIG"]
        else:
            os.environ["SERVER_ENV_CONFIG"] = old_env_server_env_config


class ContractRelatedPaymentTokenUniquifyTC(PaymentTokenUniquifyTC):
    def setUp(self):
        """Setup test data: two partners of self.company_s1 have a token
        and a contract using it:

          * first token is the main one of the contract's partner
          * second token is directly linked to the contract
        """
        super().setUp()

        token1 = self.new_payment_token(self.company_s1_w1)
        self.contract1 = self.new_contract(self.company_s1_w1)
        self.company_s1_w1.payment_token_id = token1.id

        token2 = self.new_payment_token(self.company_s1_w2, set_as_partner_token=False)
        self.contract2 = self.new_contract(self.company_s1_w2)
        self.contract2.payment_token_id = token2.id

    def new_contract(self, partner):
        product = self.env.ref("product.product_product_1")
        return self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": partner.id,
                "invoice_partner_id": partner.id,
                "pricelist_id": partner.property_product_pricelist.id,
                "contract_type": "sale",
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Services from #START# to #END#",
                            "quantity": 1,
                            "uom_id": product.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2018-02-15",
                            "recurring_next_date": "2018-02-15",
                        },
                    )
                ],
            }
        )
