import unittest
from contextlib import contextmanager

import websocket

import odoo.tests
from odoo.tests.common import ChromeBrowser

from odoo.addons.commown_devices.tests.common import DeviceAsAServiceTC


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


class RunTourMixin:
    def _run_tour(self, name):
        js = "odoo.__DEBUG__.services['web_tour.tour'].run('%s')" % name
        js_ready = "odoo.__DEBUG__.services['web_tour.tour'].tours.%s.ready" % name
        with chrome_suppress_origin():
            self.phantom_js("/my", js, js_ready, login="portal")


@odoo.tests.tagged("post_install", "-at_install")
class TestPageTC(RunTourMixin, odoo.tests.HttpCase):
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


class TestPageFP2(TestPageTC):
    contract_name = "FP2/B2C"

    def test_fp2_battery_inf_80(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_inf_80")

    def test_fp2_battery_sup_80(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_sup_80")

    def test_fp2_battery_contact_human(self):
        self._run_tour("commown_self_troubleshooting_tour_fp2_battery_contact_human")


class TestPageSmartphone(TestPageTC):
    contract_name = "FP3/B2C"

    def test_smartphone_need_screen_protection(self):
        self._run_tour("commown_self_troubleshooting_smartphone_need_screen_protection")

    def test_smartphone_need_display_with_protection(self):
        self._run_tour(
            "commown_self_troubleshooting_smartphone_need_display_with_protection"
        )

    def test_need_new_fairphone(self):
        self.contract_name = "FP5/B2C"
        self._run_tour("commown_self_troubleshooting_need_new_fairphone")


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


class TestPageRealContractTC(RunTourMixin, DeviceAsAServiceTC, odoo.tests.HttpCase):
    def test_theft_and_loss(self):
        lot = self.adjust_stock(serial="S/N-001")
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        contract.send_devices(lot, {}, date="2023-09-01", do_transfer=True)
        contract.date_start = "2023-09-01"
        self._run_tour("commown_self_troubleshooting_tour_theft_and_loss")


class TestPageGSDay(TestPageTC):
    contract_name = "GS/B2C"

    def test_gs_day_audio(self):
        self._run_tour("commown_self_troubleshooting_tour_gs_day_audio")


class TestPageCommercialRequest:
    def test_commercial_request(self):
        self._run_tour("commown_self_troubleshooting_tour_commercial_request")
