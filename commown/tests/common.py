import os
from contextlib import contextmanager

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import get_db_name

from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC
from odoo.addons.product_rental.tests.common import MockedEmptySessionMixin
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


class PortalMixin(MockedEmptySessionMixin):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        self.partner.signup_prepare()
        self.env.cr.commit()
        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        self.headers = {}

    def get_page(self, test_client, path, **data):
        "Return an lxml doc obtained from the html at given url path"
        response = test_client.get(
            path,
            query_string=data,
            follow_redirects=True,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, " - ".join((path, response.status)))
        return html.fromstring(response.data)

    def get_form(self, test_client, path, **data):
        "Get given page and return a name: value dict of its inputs and selects"
        page = self.get_page(test_client, path, **data)
        form = {n.get("name"): n.get("value") for n in page.xpath("//input")}
        for select in page.xpath("//select"):
            form[select.get("name")] = select.xpath("string(option[@selected]/@value)")
        return form

    def portal_client(self):
        user = self.partner.user_ids.ensure_one()
        test_client = Client(wsgi_server.application, BaseResponse)

        login_form = self.get_form(test_client, "/web/login/", db=get_db_name())
        login_form.update(
            {
                "login": user.login,
                "password": "portal",
                "redirect": "/my/account",
            }
        )
        response = test_client.post(
            "/web/login/",
            data=login_form,
            environ_base=self.werkzeug_environ,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/account", str(response.data))
        return test_client
