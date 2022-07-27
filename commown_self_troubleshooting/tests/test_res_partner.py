import datetime

from odoo.addons.product_rental.models.sale_order_line import NO_DATE
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


def _normalize_all_data(data):
    "Modify data in-place and return it"
    for cat_data in data:
        for page in cat_data["pages"]:
            del page["description"]
    return data


class TroubleshootingDataTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.res_partner_3")
        self.contract_fp2 = self._rental_contract("FP2")
        self.contract_serenity = self._rental_contract("FP4", "Option Sérénité")

    def _rental_contract(self, base_name, extended_product_name="", date_start=None):
        """Create and return a rental contract starting at `date_start`
        (defaults to today)

        The contract is generated from the sale order of a rental product based
        on a contract template. Those entity names are based on given base_name.
        The product name may be completed with given extended_product_name to
        simulate a variant name (useful for the Sérénité option).
        """
        contract_tmpl = self._create_rental_contract_tmpl(
            1,
            name=base_name + "/B2C",
            contract_line_ids=[self._contract_line(1, "HaaS 1 month")],
        )
        product = self._create_rental_product(
            name=(base_name + " " + extended_product_name).strip(),
            property_contract_template_id=contract_tmpl,
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [self._oline(product)],
            }
        )
        so.action_confirm()

        contract = self.env["contract.contract"].of_sale(so).ensure_one()

        contract.contract_line_ids.update(
            {
                "date_start": date_start or datetime.date.today(),
            }
        )
        contract._compute_date_end()

        return contract

    def test_all_data(self):
        data = self.partner.self_troubleshooting_all_data()
        self.assertEqual(
            _normalize_all_data(data),
            [
                {
                    "title": "Vie de mes contrats",
                    "pages": [
                        {"url_path": "/page/self-troubleshoot-contract-termination"},
                    ],
                },
                {
                    "title": "Fairphone 2",
                    "pages": [
                        {"url_path": "/page/self-troubleshoot-fp2-battery"},
                        {"url_path": "/page/self-troubleshoot-fp2-camera"},
                        {"url_path": "/page/self-troubleshoot-fp2-micro"},
                    ],
                },
                {
                    "title": "Option Sérénité",
                    "pages": [{"url_path": "/page/self-troubleshoot-serenity"}],
                },
            ],
        )

    def test_fp2_battery(self):
        get_contracts = self.partner.self_troubleshooting_contracts

        self.assertEqual(get_contracts("fp2-battery"), self.contract_fp2)

        # Check not started contracts are not returned
        self.contract_fp2.recurring_next_date = NO_DATE
        self.contract_fp2.date_start = NO_DATE

        # Check ended contracts are not returned
        self.contract_fp2.contract_line_ids.update(
            {
                "date_start": datetime.date(2020, 1, 1),
                "date_end": datetime.date(2021, 1, 1),
            }
        )
        self.assertFalse(get_contracts("fp2-battery"))

    def test_serenity(self):
        get_contracts = self.partner.self_troubleshooting_contracts
        self.assertEqual(get_contracts("serenity"), self.contract_serenity)
