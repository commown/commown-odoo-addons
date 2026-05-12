from odoo_test_helper import FakeModelLoader

from odoo.fields import Command
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
            err_msg = "Incorrect value %r for contract line field %r" % (value, attr)
            self.assertEqual(contract.contract_line_ids.mapped(attr), value, err_msg)

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

    def check_contract_lines_analytic_distribution(self, contract):
        for cline in contract.contract_line_ids:
            distribution = cline.analytic_distribution
            self.assertEqual(list(distribution.values()), [100.0])
            aa = self.env["account.analytic.account"].browse(
                int(list(distribution.keys())[0])
            )
            self.assertEqual(aa.exists().name, contract.name)

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
            },
        )
        self.check_contract_lines_analytic_distribution(c1)

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
        self.check_contract_lines_analytic_distribution(c2)

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
        self.check_contract_lines_analytic_distribution(c3)

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
        self.check_contract_lines_analytic_distribution(c4)

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
        self.check_contract_lines_analytic_distribution(c5)

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
                    2,
                    "1 month of ##ACCESSORY##",
                    tax,
                    quantity=12,  # Important!
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

    def test_pure_service(self):
        pt = self.env.ref("product_rental.prod_pc")
        pt.update({"recurrent_payment_amount": 5.0, "list_price": 0.0})
        ptav = pt.attribute_line_ids[0].product_template_value_ids[0]
        ptav.price_extra = 1.0

        product = pt.product_variant_ids.filtered(
            lambda p: ptav in p.product_template_attribute_value_ids
        )
        partner = self.env.ref("base.res_partner_3")
        so = self.env["sale.order"].create(
            {"partner_id": partner.id, "order_line": [self._oline(product)]}
        )
        so.action_confirm()

        contract = self.env["contract.contract"].of_sale(so)[0]
        self.assertEqual(contract.contract_line_ids.price_unit, 6.0)


class SaleOrderAttachmentsTC(RentalSaleOrderTC):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.res_partner_3")
        self.env["res.lang"]._activate_lang("fr_FR")
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

    def _create_simple_order(self, products):
        user_demo = self.env.ref("base.user_demo")
        return self.env["sale.order"].create(
            {
                "partner_id": user_demo.partner_id.id,
                "state": "draft",
                "order_line": [
                    Command.create(
                        {
                            "product_id": pt.id,
                        }
                    )
                    for pt in products
                ],
            }
        )

    def test_compute_order_only_services(self):
        service = self.env["product.product"].search(
            [("type", "=", "service")], limit=1
        )
        product = self.env["product.product"].search([("type", "=", "consu")], limit=1)
        order_only_service = self._create_simple_order(service)
        order_mix = self._create_simple_order(service + product)

        self.assertTrue(order_only_service.only_services)
        self.assertFalse(order_mix.only_services)

    def get_confirmation_email_attachments(self, lang):
        self.partner.lang = lang
        self.so.with_context(lang=lang)._send_order_confirmation_mail()

        # Checking the sent mail is indeed the confirmation mail template
        confirm_msg = self.so.message_ids[0]
        self.assertIn(
            f"Réf. {self.so.name} : Les prochaines étapes pour finaliser !",
            confirm_msg.subject,
        )

        return sorted(confirm_msg.attachment_ids.mapped("name"))

    def test_sale_confirmation_send_emails_fr(self):
        self.assertEqual(
            self.get_confirmation_email_attachments("fr_FR"),
            ["doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"],
        )

    def test_sale_confirmation_send_emails_en(self):
        self.assertEqual(
            self.get_confirmation_email_attachments("en_US"),
            ["doc1_en.txt", "doc_no_lang.txt"],
        )

    def test_sale_confirmation_send_emails_no_lang(self):
        self.assertEqual(
            self.get_confirmation_email_attachments(False),
            ["doc1_en.txt", "doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"],
        )
