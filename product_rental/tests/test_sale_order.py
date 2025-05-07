from odoo_test_helper import FakeModelLoader

from odoo.tests.common import tagged

from .common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class SaleOrderContractGenerationTC(RentalSaleOrderTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a fake model to override PaymentTransaction method
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from odoo.addons.contract_payment_auto.tests.models import TransactionTest

        cls.loader.update_registry((TransactionTest,))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def assert_contract_lines_attributes_equal(self, contract, value_dict):
        for attr, value in value_dict.items():
            self.assertEqual(contract.contract_line_ids.mapped(attr), value)

    def assert_rounded_equals(self, actual, expected, figures=2):
        self.assertEqual(round(actual, figures), expected)

    def new_tax(self, amount):
        name = "Tax %.02f%%" % amount
        tax = self.env["account.tax"].create(
            {
                "amount": amount,
                "amount_type": "percent",
                "price_include": True,  # french style
                "name": name,
                "description": name,
                "type_tax_use": "sale",
            }
        )
        return tax

    def test_rental_contract_creation_without_fpos(self):
        """Contracts generated from rental sales have specific characteristics

        We use tax-included in the price for tests (french
        style). Company's default tax is used for products without a
        specific tax (see sale.order.line `compute_recurrent_payment_amount` method doc)

        """
        tax = self.new_tax(20.0)
        i5, i4, i3, i2, i1 = invs = self.generate_contract_invoices(tax=tax).sorted(
            "id", reverse=True
        )
        c5, c4, c3, c2, c1 = invs.mapped(
            "invoice_line_ids.contract_line_id.contract_id"
        )

        self.assert_rounded_equals(i1.amount_total, 26.50)
        self.assert_rounded_equals(i1.amount_untaxed, 22.08)

        self.assert_contract_lines_attributes_equal(
            c1,
            {
                "name": ["1 month Fairphone premium", "1 month headset"],
                "price_unit": [25.0, 1.5],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": ["Fairphone Premium", "headset"],
                "contract_id.group_id.name": [c1.name],
                "contract_id.group_id.partner_id": c1.partner_id,
            },
        )

        self.assert_rounded_equals(i2.amount_total, 87.90)
        self.assert_rounded_equals(i2.amount_untaxed, 73.25)

        self.assert_contract_lines_attributes_equal(
            c2,
            {
                "name": [
                    "1 month of PC",
                    "1 month of screen",
                    "1 month of keyboard",
                    "1 month of keyboard deluxe",
                ],
                "price_unit": [60.0, 15.0, 5.4, 7.5],
                "quantity": [1, 1, 1, 1],
                "sale_order_line_id.product_id.name": [
                    "PC",
                    "screen",
                    "keyboard",
                    "keyboard deluxe",
                ],
                "contract_id.group_id.name": [c2.name],
                "contract_id.group_id.partner_id": c2.partner_id,
            },
        )

        self.assert_rounded_equals(i3.amount_total, 75.0)
        self.assert_rounded_equals(i3.amount_untaxed, 62.5)

        self.assert_contract_lines_attributes_equal(
            c3,
            {
                "name": ["1 month of PC", "1 month of screen"],
                "price_unit": [60.0, 15.0],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": ["PC", "screen"],
                "contract_id.group_id.name": [c3.name],
                "contract_id.group_id.partner_id": c3.partner_id,
            },
        )

        self.assert_rounded_equals(i4.amount_total, 16.0)
        self.assert_rounded_equals(i4.amount_untaxed, 13.33)

        self.assert_contract_lines_attributes_equal(
            c4,
            {
                "name": ["1 month of GS Headset", "1 month of serenity level services"],
                "price_unit": [10.0, 6.0],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": [
                    "GS Headset",
                    "serenity level services",
                ],
                "contract_id.group_id.name": [c4.name],
                "contract_id.group_id.partner_id": c4.partner_id,
            },
        )

        self.assert_rounded_equals(i5.amount_total, 50.0)
        self.assert_rounded_equals(i5.amount_untaxed, 41.67)

        self.assert_contract_lines_attributes_equal(
            c5,
            {
                "name": ["1 month of FP2", "1 month of screen"],
                "price_unit": [20.0, 15.0],
                "quantity": [1, 2],
                "sale_order_line_id.product_id.name": ["FP2", "screen"],
                "contract_id.group_id.name": [c5.name],
                "contract_id.group_id.partner_id": c5.partner_id,
            },
        )

    def test_rental_contract_creation_with_fpos(self):
        partner = self.env.ref("base.res_partner_3")

        tax_src = self.new_tax(5.0)  # should never be used
        tax_dest = self.new_tax(20.0)

        afp_model = self.env["account.fiscal.position"]
        partner.property_account_position_id = afp_model.create(
            {
                "name": "test_fpos",
                "tax_ids": [
                    (
                        0,
                        0,
                        {
                            "tax_src_id": tax_src.id,
                            "tax_dest_id": tax_dest.id,
                        },
                    ),
                ],
            }
        )

        i5, i4, i3, i2, i1 = invs = self.generate_contract_invoices(
            partner, tax_src
        ).sorted("id", reverse=True)

        c5, c4, c3, c2, c1 = invs.mapped(
            "invoice_line_ids.contract_line_id.contract_id"
        )

        self.assert_rounded_equals(i1.amount_total, 26.50)
        self.assert_rounded_equals(i1.amount_untaxed, 22.08)

        self.assert_contract_lines_attributes_equal(
            c1,
            {
                "name": ["1 month Fairphone premium", "1 month headset"],
                "price_unit": [25.0, 1.5],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": ["Fairphone Premium", "headset"],
            },
        )

        self.assert_rounded_equals(i2.amount_total, 87.90)
        self.assert_rounded_equals(i2.amount_untaxed, 73.25)

        self.assert_contract_lines_attributes_equal(
            c2,
            {
                "name": [
                    "1 month of PC",
                    "1 month of screen",
                    "1 month of keyboard",
                    "1 month of keyboard deluxe",
                ],
                "price_unit": [60.0, 15.0, 5.4, 7.5],
                "quantity": [1, 1, 1, 1],
                "sale_order_line_id.product_id.name": [
                    "PC",
                    "screen",
                    "keyboard",
                    "keyboard deluxe",
                ],
            },
        )

        self.assert_rounded_equals(i3.amount_total, 75.0)
        self.assert_rounded_equals(i3.amount_untaxed, 62.5)

        self.assert_contract_lines_attributes_equal(
            c3,
            {
                "name": ["1 month of PC", "1 month of screen"],
                "price_unit": [60.0, 15.0],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": ["PC", "screen"],
            },
        )

        self.assert_rounded_equals(i4.amount_total, 16.0)
        self.assert_rounded_equals(i4.amount_untaxed, 13.33)

        self.assert_contract_lines_attributes_equal(
            c4,
            {
                "name": ["1 month of GS Headset", "1 month of serenity level services"],
                "price_unit": [10.0, 6.0],
                "quantity": [1, 1],
                "sale_order_line_id.product_id.name": [
                    "GS Headset",
                    "serenity level services",
                ],
            },
        )

        self.assert_rounded_equals(i5.amount_total, 50.0)
        self.assert_rounded_equals(i5.amount_untaxed, 41.67)

        self.assert_contract_lines_attributes_equal(
            c5,
            {
                "name": ["1 month of FP2", "1 month of screen"],
                "price_unit": [20.0, 15.0],
                "quantity": [1, 2],
                "sale_order_line_id.product_id.name": ["FP2", "screen"],
            },
        )

    def test_yearly_with_accessory(self):
        "Accessories priced monthly: contract template quantity to be honored"

        partner = self.env.ref("base.res_partner_3")
        tax = self.get_default_tax()

        contract_tmpl = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                self._contract_line(
                    1, "1 year of ##PRODUCT##", tax, specific_price=0.0
                ),
                self._contract_line(
                    2, "1 month of ##ACCESSORY##", tax, quantity=12  # Important!
                ),
            ],
        )

        headset = self._create_rental_product(
            name="GS Headset",
            list_price=1.0,
            recurrent_payment_amount=75.0,
            property_contract_template_id=contract_tmpl.id,
        )
        oline_p = self._oline(headset)

        micro = self._create_rental_product(
            name="micro",
            list_price=3.0,
            recurrent_payment_amount=1.5,
            property_contract_template_id=False,
        )
        oline_a = self._oline(micro)

        headset.accessory_product_ids |= micro

        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [oline_p, oline_a],
            }
        )

        so.action_confirm()
        contracts = self.env["contract.contract"].of_sale(so)

        self.assertEqual(len(contracts), 1)
        self.assertEqual(
            [(line.name, line.quantity) for line in contracts.contract_line_ids],
            [("1 year of GS Headset", 1.0), ("1 month of micro", 12.0)],
        )

    def test_rental_taxes(self):
        """Check rental and price taxes roles

        - rental product rental price tax is used to compute contract line price which
          must be interpreted without tax.

        - contract product normal price tax is used to compute invoice price which must
          be interpreted like the price tax (according to its price_include field value.
        """

        partner = self.env.ref("base.res_partner_3")
        rental_tax = self.get_default_tax()
        assert (rental_tax.amount, rental_tax.price_include) == (20.0, True)
        tax = rental_tax.copy({"price_include": False})

        ct = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[self._contract_line(1, "1 month ##PRODUCT##", tax)],
        )

        product = self._create_rental_product(
            name="Fairphone",
            list_price=60.0,
            recurrent_payment_amount=30.0,
            recurrent_payment_tax_ids=[(6, 0, rental_tax.ids)],
            property_contract_template_id=ct.id,
        )

        so = self.env["sale.order"].create(
            {"partner_id": partner.id, "order_line": [self._oline(product)]}
        )
        so.action_confirm()

        contract = self.env["contract.contract"].of_sale(so)[0]
        cline = contract.contract_line_ids
        self.assertEqual(cline.specific_price, 25.0)

        inv = contract.recurring_create_invoice()
        self.assertEqual(inv.amount_total, 30.0)
        self.assertEqual(inv.amount_tax, 5.0)

    def test_automatic_payment(self):
        so = self.create_sale_order()
        so.action_confirm()

        provider = self.env.ref("payment.payment_provider_transfer")

        token = self.env["payment.token"].create(
            {
                "payment_details": "Test Token",
                "partner_id": so.partner_id.id,
                "active": True,
                "provider_id": provider.id,
                "provider_ref": "my_ref",
            }
        )

        customer_journal = self.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": self.env.company.id,
                "type": "bank",
            }
        )

        pay_meth = customer_journal.inbound_payment_method_line_ids.mapped(
            "payment_method_id"
        )

        pay_mode = self.env["account.payment.mode"].create(
            {
                "name": "Automatic contract payment",
                "payment_method_id": pay_meth.id,
                "payment_type": "inbound",
                "bank_account_link": "fixed",
                "fixed_journal_id": customer_journal.id,
            }
        )

        contract = self.env["contract.contract"].of_sale(so)[0]
        contract.update(
            {
                "is_auto_pay": True,
                "payment_token_id": token.id,
                "payment_mode_id": pay_mode.id,
            }
        )

        contract.with_context(test_target_state="done").recurring_create_invoice()

        # Do not use _recurring_create_invoice return value here as
        # contract_queue_job (installed in the CI) returns an empty invoice set
        # (see https://github.com/OCA/contract/blob/12.0/contract_queue_job
        #  /models/contract_contract.py#L21)
        inv = self.env["account.move"].search(
            [
                ("line_ids.contract_line_id.contract_id", "=", contract.id),
            ]
        )
        self.assertEqual(inv.state, "posted")


class SaleOrderAttachmentsTC(RentalSaleOrderTC):
    def setUp(self):
        super(SaleOrderAttachmentsTC, self).setUp()
        self.partner = self.env.ref("base.res_partner_3")
        self.env["res.lang"].load_lang("fr_FR")
        self.so = self.create_sale_order(self.partner)
        ct = self.so.mapped("order_line.product_id.property_contract_template_id")[0]
        ct.contractual_documents |= self.create_attachment("doc1_fr.txt", "fr_FR")
        ct.contractual_documents |= self.create_attachment("doc2_fr.txt", "fr_FR")
        ct.contractual_documents |= self.create_attachment("doc1_en.txt", "en_US")
        ct.contractual_documents |= self.create_attachment("doc_no_lang.txt", False)
        # Remove report from default template to make it possible to add ours:
        self.env.ref("sale.email_template_edi_sale").report_template = False

    def create_attachment(self, name, lang):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": "toto",
                "lang": lang,
                "public": True,
            }
        )

    def check_sale_quotation_send_emails(self, lang):
        self.partner.lang = lang
        self.so.with_context(lang=lang).action_quotation_send()
        email_act = self.so.action_quotation_send()
        email_ctx = email_act["context"]
        self.so.with_context(**email_ctx).message_post_with_template(
            email_ctx.get("default_template_id")
        )
        return sorted(self.so.message_ids[0].attachment_ids.mapped("name"))

    def test_sale_quotation_send_emails_fr(self):
        """break /usr/lib/python3/dist-packages/odoo/models.py:1148"""
        self.assertEqual(
            self.check_sale_quotation_send_emails("fr_FR"),
            ["doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"],
        )

    def test_sale_quotation_send_emails_en(self):
        self.assertEqual(
            self.check_sale_quotation_send_emails("en_US"),
            ["doc1_en.txt", "doc_no_lang.txt"],
        )

    def test_sale_quotation_send_emails_no_lang(self):
        self.assertEqual(
            self.check_sale_quotation_send_emails(False),
            ["doc1_en.txt", "doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"],
        )
