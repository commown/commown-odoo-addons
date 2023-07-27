from contextlib import contextmanager

import websocket

import odoo.tests
from odoo.tests.common import ChromeBrowser


@contextmanager
def chrome_suppress_origin():
    old_open_websocket = ChromeBrowser._open_websocket

    def new_open_websocket(self):
        self.ws = websocket.create_connection(self.ws_url, suppress_origin=True)
        if self.ws.getstatus() != 101:
            raise unittest.SkipTest("Cannot connect to chrome dev tools")
        self.ws.settimeout(0.01)

    ChromeBrowser._open_websocket = new_open_websocket
    try:
        yield
    finally:
        ChromeBrowser._open_websocket = old_open_websocket


@odoo.tests.tagged("post_install", "-at_install")
class TestPageTC(odoo.tests.HttpCase):
    "Base class to ease tour test writting"

    contract_name = None  # Override me!

    def create_contract(self, name, product, user, date_start="2020-01-01"):
        partner = user.partner_id
        ct = self.env["contract.template"].create({"name": name})
        cline_attrs = {
            "name": "Line 1",
            "specific_price": 1.0,
            "quantity": 1.0,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "product_id": product.id,
            "date_start": date_start,
        }

        contract = self.env["contract.contract"].create(
            {
                "name": "SO0000 Test Contract",
                "partner_id": partner.id,
                "contract_template_id": ct.id,
                "contract_line_ids": [(0, 0, cline_attrs)],
            }
        )
        contract.message_subscribe(partner_ids=user.partner_id.ids)
        return contract

    def setUp(self):
        super().setUp()
        user_portal = self.env.ref("base.demo_user0")
        product = self.env["product.product"].create(
            {"name": "Test service product", "type": "service"}
        )
        if self.contract_name:
            self.contract = self.create_contract(
                self.contract_name,
                product,
                user_portal,
            )

    def _run_tour(self, name):
        js = "odoo.__DEBUG__.services['web_tour.tour'].run('%s')" % name
        js_ready = "odoo.__DEBUG__.services['web_tour.tour'].tours.%s.ready" % name
        with chrome_suppress_origin():
            self.phantom_js("/my", js, js_ready, login="portal")


class TestPageFP2(TestPageTC):
    contract_name = "FP2/B2C"

    def test_fp2_battery_inf_80(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_inf_80")

    def test_fp2_battery_sup_80(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_sup_80")

    def test_fp2_battery_contact_human(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_contact_human")


class TestPageContractManagement(TestPageTC):
    contract_name = "NO/MATTER"

    def test_termination_no_commitment(self):
        self._run_tour("commown_self_troubleshooting_tour_termination_no_commitment")

    def test_termination_with_commitment_transfer(self):
        self.contract.commitment_period_number = 240
        self._run_tour(
            "commown_self_troubleshooting_tour_termination_commitment_transfer"
        )

    def test_termination_with_commitment_pay(self):
        self.contract.commitment_period_number = 240
        self._run_tour("commown_self_troubleshooting_tour_termination_commitment_pay")
