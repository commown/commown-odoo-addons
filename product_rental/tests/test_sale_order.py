from mock import patch

from odoo.tests.common import at_install, post_install

from odoo.addons.payment.models.payment_acquirer import PaymentTransaction

from .common import RentalSaleOrderTC


def fake_s2s_do_transaction(self, **kwargs):
    for tx in self:
        tx._set_transaction_done()
        tx._post_process_after_done()
        return True


@at_install(False)
@post_install(True)
class SaleOrderContractGenerationTC(RentalSaleOrderTC):
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
        specific tax (see sale.order.line `compute_rental_price` method doc)

        """
        tax = self.new_tax(20.0)
        i5, i4, i3, i2, i1 = invs = self.generate_contract_invoices(tax=tax)
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
                "analytic_account_id.name": [c1.name],
                "analytic_account_id.partner_id": c1.partner_id,
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
                "analytic_account_id.name": [c2.name],
                "analytic_account_id.partner_id": c2.partner_id,
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
                "analytic_account_id.name": [c3.name],
                "analytic_account_id.partner_id": c3.partner_id,
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
                "analytic_account_id.name": [c4.name],
                "analytic_account_id.partner_id": c4.partner_id,
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
                "analytic_account_id.name": [c5.name],
                "analytic_account_id.partner_id": c5.partner_id,
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

        i5, i4, i3, i2, i1 = invs = self.generate_contract_invoices(partner, tax_src)
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
            rental_price=75.0,
            property_contract_template_id=contract_tmpl.id,
        )
        oline_p = self._oline(headset)

        micro = self._create_rental_product(
            name="micro",
            list_price=3.0,
            rental_price=1.5,
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
        self.assertEquals(
            [(l.name, l.quantity) for l in contracts.contract_line_ids],
            [("1 year of GS Headset", 1.0), ("1 month of micro", 12.0)],
        )

    def test_automatic_payment(self):
        so = self.create_sale_order()
        so.action_confirm()

        acquirer = self.env.ref("payment.payment_acquirer_transfer")

        token = self.env["payment.token"].create(
            {
                "name": "Test Token",
                "partner_id": so.partner_id.id,
                "active": True,
                "acquirer_id": acquirer.id,
                "acquirer_ref": "my_ref",
            }
        )

        customer_journal = self.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": self.env.user.company_id.id,
                "type": "bank",
                "update_posted": True,
            }
        )

        pay_meth = self.env.ref("payment.account_payment_method_electronic_in")

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

        with patch.object(
            PaymentTransaction, "s2s_do_transaction", new=fake_s2s_do_transaction
        ):
            contract.recurring_create_invoice()

        # Do not use _recurring_create_invoice return value here as
        # contract_queue_job (installed in the CI) returns an empty invoice set
        # (see https://github.com/OCA/contract/blob/12.0/contract_queue_job
        #  /models/contract_contract.py#L21)
        inv = self.env["account.invoice"].search(
            [
                ("invoice_line_ids.contract_line_id.contract_id", "=", contract.id),
            ]
        )
        self.assertEqual(inv.state, "paid")


class SaleOrderAttachmentsTC(RentalSaleOrderTC):
    def setUp(self):
        super(SaleOrderAttachmentsTC, self).setUp()
        self.partner = self.env.ref("base.res_partner_3")
        self.env["res.lang"].load_lang("fr_FR")
        self.env["res.lang"].pool.cache.clear()
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
        self.so.force_quotation_send()
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
