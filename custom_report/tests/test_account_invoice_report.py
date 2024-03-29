import re

from .common import ReportTC


def _product_descriptions(invoice_doc):
    return [
        descr
        for descr in invoice_doc.xpath("//tbody//tr//td[1]//text()")
        if descr.strip()
    ]


class AccountInvoiceReportTC(ReportTC):
    report_name = "account.report_invoice"

    def setUp(self):
        super().setUp()
        self.b2c_partner = self.env.ref("base.partner_demo_portal")
        self.b2b_partner = self.partner = self.env.ref("base.res_partner_address_1")

        deposit_account = self.env.ref("l10n_fr.1_pcg_2751")

        categ_deposit = self.env["product.category"].create(
            {
                "name": "Deposits",
                "property_account_income_categ_id": deposit_account,
                "property_account_expense_categ_id": deposit_account,
            }
        )

        self.deposit_product = self.env["product.product"].create(
            {
                "name": "FP2 Premium",
                "is_rental": True,
                "type": "service",
                "list_price": 60,
                "categ_id": categ_deposit.id,
            }
        )

        self.equity_product = self.env["product.product"].create(
            {
                "name": "Coop Part",
                "is_equity": True,
                "type": "service",
                "list_price": 20,
            }
        )

        self.std_product = self.env["product.product"].create(
            {
                "name": "Std product",
                "type": "service",
                "list_price": 1,
            }
        )

    def sale(self, partner, products):
        olines = []
        for product in products:
            olines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom": product.uom_id.id,
                        "name": product.name,
                        "product_uom_qty": 1,
                        "price_unit": product.list_price,
                    },
                )
            )
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": olines,
            }
        )
        so.action_confirm()
        return so

    def open_invoice(self, so, is_refund=False, contract=None):
        inv = self.env["account.invoice"].browse(so.action_invoice_create())
        if is_refund:
            inv.type = "out_refund"
        if contract:
            cline = contract.contract_line_ids[0]
            inv.invoice_line_ids.update(
                {
                    "contract_line_id": cline.id,
                    "account_analytic_id": cline.analytic_account_id.id,
                }
            )
        inv.action_invoice_open()
        return inv

    def test_b2c_deposit(self):
        inv = self.open_invoice(self.sale(self.b2c_partner, [self.deposit_product]))
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Certificate %s" % inv.display_name.strip()]
        )

    def test_b2c_equity(self):
        inv = self.open_invoice(self.sale(self.b2c_partner, [self.equity_product]))
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Certificate %s" % inv.display_name.strip()]
        )

    def test_b2c_std_product(self):
        inv = self.open_invoice(self.sale(self.b2c_partner, [self.std_product]))
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Invoice %s" % inv.display_name.strip()]
        )

    def test_b2c_from_contract(self):
        cname, partner = "Test Contract", self.b2c_partner

        aa = self.env["account.analytic.account"].create(
            {"name": cname, "partner_id": partner.id}
        )

        contract = self.env["contract.contract"].create(
            {
                "name": cname,
                "partner_id": partner.id,
                "pricelist_id": self.b2c_partner.property_product_pricelist.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line 1",
                            "product_id": self.std_product.id,
                            "analytic_account_id": aa.id,
                        },
                    )
                ],
            }
        )
        so = self.sale(self.b2c_partner, [self.std_product])
        inv = self.open_invoice(so, contract=contract)
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Invoice %s" % inv.display_name.strip()]
        )
        first_inv_line_descr = (
            doc.xpath(
                "//thead//b[text()='Description']/ancestor::table[1]"
                "/tbody/tr[1]/td[1]"
            )[0]
            .text_content()
            .strip()
        )
        # Internal spaces/ tabs in a text html node are not
        # significant: replace them by a single space
        self.assertEqual(
            re.sub(r"\s\s+", " ", first_inv_line_descr),
            "Contract Test Contract - Std product",
        )

    def test_b2c_refund(self):
        inv = self.open_invoice(
            self.sale(self.b2c_partner, [self.std_product]), is_refund=True
        )
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Refund %s" % inv.display_name.strip()]
        )

    def test_b2b_refund(self):
        inv = self.open_invoice(
            self.sale(self.b2b_partner, [self.std_product]), is_refund=True
        )
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Refund %s" % inv.display_name.strip()]
        )

    def test_b2b_deposit(self):
        inv = self.open_invoice(self.sale(self.b2b_partner, [self.deposit_product]))
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Invoice %s" % inv.display_name.strip()]
        )

    def test_b2b_std_product(self):
        inv = self.open_invoice(self.sale(self.b2b_partner, [self.std_product]))
        doc = self.html_report(inv)
        self.assertEqual(
            doc.xpath("//h1/text()"), ["Invoice %s" % inv.display_name.strip()]
        )

    def test_b2c_qty_zero(self):
        "Invoice lines with quantity equal to zero must not appear on invoice"
        so1 = self.sale(self.b2c_partner, [self.std_product, self.std_product])
        inv1 = self.open_invoice(so1)
        doc1 = self.html_report(inv1)

        self.assertEqual(
            _product_descriptions(doc1), [self.std_product.name] * 2
        )  # 2 product lines

        so2 = self.sale(self.b2c_partner, [self.std_product, self.std_product])
        so2.order_line[1].product_uom_qty = 0  # Quantity 0 for second product
        inv2 = self.open_invoice(so2)
        doc2 = self.html_report(inv2)

        self.assertEqual(
            _product_descriptions(doc2), [self.std_product.name]
        )  # 1 product line only
