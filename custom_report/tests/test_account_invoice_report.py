import re

from lxml.etree import tostring

from .common import ReportTC


def _product_descriptions(invoice_doc):
    return [
        descr
        for descr in invoice_doc.xpath("//tbody//tr//td[1]//text()")
        if descr.strip()
    ]


class AccountInvoiceReportTC(ReportTC):
    report_name = "account.report_invoice"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.b2c_partner = cls.env.ref("base.partner_demo_portal")
        cls.b2b_partner = cls.partner = cls.env.ref("base.res_partner_address_1")

        if not cls.env.company.chart_template_id:  # pragma: no cover
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
                coa.try_loading(company=cls.env.company, install_demo=True)

        deposit_account = cls.env["account.account"].search(
            [
                ("code", "=", 275100),
                ("company_id", "=", cls.env.company.id),
            ]
        )

        categ_deposit = cls.env["product.category"].create(
            {
                "name": "Deposits",
                "property_account_income_categ_id": deposit_account,
                "property_account_expense_categ_id": deposit_account,
            }
        )

        cls.deposit_product = cls.env["product.product"].create(
            {
                "name": "FP2 Premium",
                "has_recurrent_payment": True,
                "type": "service",
                "list_price": 60,
                "categ_id": categ_deposit.id,
            }
        )

        cls.equity_product = cls.env["product.product"].create(
            {
                "name": "Coop Part",
                "is_equity": True,
                "type": "service",
                "list_price": 20,
            }
        )

        cls.std_product = cls.env["product.product"].create(
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

    def open_invoice(self, so, is_refund=False, contract=None, post_invoice=True):
        inv = so._create_invoices()
        if is_refund:
            inv.move_type = "out_refund"
        if contract:
            cline = contract.contract_line_ids[0]
            inv.line_ids.update(
                {
                    "contract_line_id": cline.id,
                    "analytic_distribution": cline.analytic_distribution,
                }
            )
        if post_invoice:
            inv.action_post()
        return inv

    def apply_tax(self, inv_line, amount):
        # Pass an invoice line and a tax amount (in percentage)
        tax = self.env["account.tax"].search(
            [
                ("amount", "=", amount),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

        inv_line.tax_ids |= tax

    def test_account_move_actions(self):
        view = self.env.ref("account.view_move_form")
        result = self.env["account.move"].get_views(
            [(view.id, "form")], {"toolbar": True}
        )

        print_actions = sorted(
            [a["name"] for a in result["views"]["form"]["toolbar"].get("print", [])]
        )

        self.assertIn(
            "[commown] Print invoice",
            print_actions,
        )
        self.assertIn(
            "[commown] Print invoice duplicata",
            print_actions,
        )

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
            {
                "name": cname,
                "partner_id": partner.id,
                "plan_id": self.env.ref("analytic.analytic_plan_projects").id,
            }
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
                            "analytic_distribution": {str(aa.id): 100},
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

    def test_invoice_0_percent_taxes(self):
        # Print invoice report with 0% tax
        inv = self.open_invoice(
            self.sale(self.b2c_partner, self.std_product), post_invoice=False
        )
        self.apply_tax(inv.invoice_line_ids, 0.0)

        tax_data = inv.tax_totals["groups_by_subtotal"].get(
            inv.tax_totals["subtotals_order"][0], {}
        )

        html_0_tax = tostring(self.html_report(inv))
        # Invoice tax table check
        self.assertTrue(b"TVA 0%" in html_0_tax)
        self.assertIn(
            bytes(str(tax_data[0].get("tax_group_base_amount")), "utf-8"),
            html_0_tax,
        )
        self.assertIn(
            bytes(str(tax_data[0].get("tax_group_amount")), "utf-8"),
            html_0_tax,
        )

        # Invoice total recap check
        self.assertFalse(b"Total Taxes" in html_0_tax)

    def test_invoice_10_percent_tax(self):
        # Print invoice report with 10% tax
        inv = self.open_invoice(
            self.sale(self.b2c_partner, self.std_product), post_invoice=False
        )
        self.apply_tax(inv.invoice_line_ids, 10.0)

        tax_data = inv.tax_totals["groups_by_subtotal"].get(
            inv.tax_totals["subtotals_order"][0], [{}]
        )

        html_10_tax = tostring(self.html_report(inv))
        # Invoice tax table check
        self.assertTrue(b"TVA 10%" in html_10_tax)
        self.assertIn(
            bytes(str(tax_data[0].get("tax_group_base_amount")), "utf-8"),
            html_10_tax,
        )
        self.assertIn(
            bytes(str(tax_data[0].get("tax_group_amount")), "utf-8"),
            html_10_tax,
        )

        # Invoice total recap check
        self.assertTrue(b"Total Taxes" in html_10_tax)
        self.assertIn(
            bytes(str(inv.amount_tax), "utf-8"),
            html_10_tax,
        )

    def test_invoice_payment_terms(self):
        ref = self.env.ref
        inv = self.open_invoice(self.sale(self.b2c_partner, self.std_product))

        inv.invoice_payment_term_id = ref("account.account_payment_term_immediate").id
        html = tostring(self.html_report(inv))
        self.assertTrue(b"Payment conditions" in html)
        self.assertTrue(b"Payment terms: Immediate" in html)

    def test_b2c_customer_invoice_address(self):
        "An invoice issue to a partner related to a company should present the partner and company names"
        # Applying a title on the partner, for coverage reasons
        self.b2c_partner.title = self.env.ref("base.res_partner_title_doctor")
        expected_name = " ".join(
            [self.b2c_partner.title.shortcut, self.b2c_partner.name]
        )

        inv = self.open_invoice(self.sale(self.b2c_partner, self.std_product))
        doc = self.html_report(inv)

        address = doc.xpath(
            f"//font[text()='{expected_name}']/ancestor::td//font/text()"
        )
        self.assertEqual(
            address,
            [
                expected_name,
            ]
            + self.b2c_partner._display_address(without_company=True).split("\n"),
        )

    def test_b2b_customer_invoice_address(self):
        "An invoice issue to a partner related to a company should present the partner and company names"
        inv = self.open_invoice(self.sale(self.b2b_partner, self.std_product))
        doc = self.html_report(inv)

        address = doc.xpath(
            f"//font[text()='{self.b2b_partner.commercial_partner_id.name}']/ancestor::td//font/text()"
        )
        self.assertEqual(
            address,
            [
                self.b2b_partner.commercial_partner_id.name,
                self.b2b_partner.name,
            ]
            + self.b2b_partner._display_address(without_company=True).split("\n"),
        )

    def test_b2b_company_invoice_address(self):
        "An invoice issued to a company should only have the company name"
        company = self.b2b_partner.commercial_partner_id

        inv = self.open_invoice(self.sale(company, self.std_product))

        doc = self.html_report(inv)
        address = doc.xpath(
            f"//font[text()='{self.b2b_partner.commercial_partner_id.name}']/ancestor::td//font/text()"
        )
        self.assertEqual(
            address,
            [
                company.name,
            ]
            + company._display_address(without_company=True).split("\n"),
        )

    def test_commercial_user_invoice_address(self):
        "The user of an invoice, the commercial partner, should have their address displayed"
        demo_partner = self.env.ref("base.partner_demo")
        demo_partner.mobile = "+123456789"

        inv = self.open_invoice(self.sale(self.b2c_partner, self.std_product))
        inv.invoice_user_id = demo_partner.user_ids

        doc = self.html_report(inv)
        # Due to a linebreak right before the salesperson's name (though it doesn't appear in the real document),
        # we strip the linebreaks and indents
        address = doc.xpath(
            f"//p[contains(text(), '{demo_partner.name}')]/ancestor::td/p/text()"
        )
        address = [line.strip() for line in address]
        self.assertEqual(
            address,
            [
                demo_partner.name,
                f"\U0001F4DE {demo_partner.phone}",
                f"\U0001F4F1 {demo_partner.mobile}",
                f"\u2709 {demo_partner.email}",
            ],
        )
