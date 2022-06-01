from .common import RentalSaleOrderTC


class SaleOrderTC(RentalSaleOrderTC):

    def assert_contract_lines_attributes_equal(self, contract, value_dict):
        for attr, value in value_dict.items():
            self.assertEqual(contract.contract_line_ids.mapped(attr), value)

    def assert_rounded_equals(self, actual, expected, figures=2):
        self.assertEqual(round(actual, figures), expected)

    def new_tax(self, amount):
        name = 'Tax %.02f%%' % amount
        tax = self.env['account.tax'].create({
            'amount': amount,
            'amount_type': 'percent',
            'price_include': True,  # french style
            'name': name,
            'description': name,
            'type_tax_use': 'sale',
        })
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
            'invoice_line_ids.contract_line_id.contract_id')

        self.assert_rounded_equals(i1.amount_total, 26.50)
        self.assert_rounded_equals(i1.amount_untaxed, 22.08)

        self.assert_contract_lines_attributes_equal(c1, {
            'name': ['1 month Fairphone premium', '1 month headset'],
            'price_unit': [25., 1.5],
            'quantity': [1, 1],
            'sale_order_line_id.product_id.name': [
                'Fairphone Premium', 'headset'],
        })

        self.assert_rounded_equals(i2.amount_total, 87.90)
        self.assert_rounded_equals(i2.amount_untaxed, 73.25)

        self.assert_contract_lines_attributes_equal(c2, {
            'name': ['1 month of PC', '1 month of screen',
                     '1 month of keyboard', '1 month of keyboard deluxe',
                     ],
            'price_unit': [60.0, 15.0, 5.4, 7.5],
            'quantity': [1, 1, 1, 1],
            'sale_order_line_id.product_id.name': [
                'PC', 'screen', 'keyboard', 'keyboard deluxe'],
        })

        self.assert_rounded_equals(i3.amount_total, 75.0)
        self.assert_rounded_equals(i3.amount_untaxed, 62.5)

        self.assert_contract_lines_attributes_equal(c3, {
            'name': [u'1 month of PC', u'1 month of screen'],
            'price_unit': [60.0, 15.0],
            'quantity': [1, 1],
            'sale_order_line_id.product_id.name': [u'PC', u'screen'],
        })

        self.assert_rounded_equals(i4.amount_total, 10.0)
        self.assert_rounded_equals(i4.amount_untaxed, 8.33)

        self.assert_contract_lines_attributes_equal(c4, {
            'name': ['1 month of GS Headset'],
            'price_unit': [10.0],
            'quantity': [1],
            'sale_order_line_id.product_id.name': ['GS Headset'],
        })

        self.assert_rounded_equals(i5.amount_total, 20.0)
        self.assert_rounded_equals(i5.amount_untaxed, 16.67)

        self.assert_contract_lines_attributes_equal(c5, {
            'name': ['1 month of FP2'],
            'price_unit': [20.0],
            'quantity': [1],
            'sale_order_line_id.product_id.name': ['FP2'],
        })

    def test_rental_contract_creation_with_fpos(self):
        partner = self.env.ref('base.res_partner_3')

        tax_src = self.new_tax(5.)  # should never be used
        tax_dest = self.new_tax(20.)

        afp_model = self.env['account.fiscal.position']
        partner.property_account_position_id = afp_model.create({
            'name': 'test_fpos',
            'tax_ids': [
                (0, 0, {
                    'tax_src_id': tax_src.id,
                    'tax_dest_id': tax_dest.id,
                }),
            ],
        })

        i5, i4, i3, i2, i1 = invs = self.generate_contract_invoices(
            partner, tax_src)
        c5, c4, c3, c2, c1 = invs.mapped(
            'invoice_line_ids.contract_line_id.contract_id')

        self.assert_rounded_equals(i1.amount_total, 26.50)
        self.assert_rounded_equals(i1.amount_untaxed, 22.08)

        self.assert_contract_lines_attributes_equal(c1, {
            'name': ['1 month Fairphone premium', '1 month headset'],
            'price_unit': [25., 1.5],
            'quantity': [1, 1],
            'sale_order_line_id.product_id.name': [
                'Fairphone Premium', 'headset'],
        })

        self.assert_rounded_equals(i2.amount_total, 87.90)
        self.assert_rounded_equals(i2.amount_untaxed, 73.25)

        self.assert_contract_lines_attributes_equal(c2, {
            'name': ['1 month of PC', '1 month of screen',
                     '1 month of keyboard', '1 month of keyboard deluxe',
                     ],
            'price_unit': [60.0, 15.0, 5.4, 7.5],
            'quantity': [1, 1, 1, 1],
            'sale_order_line_id.product_id.name': [
                'PC', 'screen', 'keyboard', 'keyboard deluxe'],
        })

        self.assert_rounded_equals(i3.amount_total, 75.0)
        self.assert_rounded_equals(i3.amount_untaxed, 62.5)

        self.assert_contract_lines_attributes_equal(c3, {
            'name': [u'1 month of PC', u'1 month of screen'],
            'price_unit': [60.0, 15.0],
            'quantity': [1, 1],
            'sale_order_line_id.product_id.name': [u'PC', u'screen'],
        })

        self.assert_rounded_equals(i4.amount_total, 10.0)
        self.assert_rounded_equals(i4.amount_untaxed, 8.33)

        self.assert_contract_lines_attributes_equal(c4, {
            'name': ['1 month of GS Headset'],
            'price_unit': [10.0],
            'quantity': [1],
            'sale_order_line_id.product_id.name': ['GS Headset'],
        })

        self.assert_rounded_equals(i5.amount_total, 20.0)
        self.assert_rounded_equals(i5.amount_untaxed, 16.67)

        self.assert_contract_lines_attributes_equal(c5, {
            'name': ['1 month of FP2'],
            'price_unit': [20.0],
            'quantity': [1],
            'sale_order_line_id.product_id.name': ['FP2'],
        })

    def test_yearly_with_accessory(self):
        " Accessories priced monthly: contract template quantity to be honored "

        partner = self.env.ref('base.res_partner_3')
        tax = self.get_default_tax()

        contract_tmpl = self._create_rental_contract_tmpl(
            1, contract_line_ids=[
                self._contract_line(
                    1, '1 year of ##PRODUCT##', tax, specific_price=0.0
                ),
                self._contract_line(
                    2, '1 month of ##ACCESSORY##', tax,
                    quantity=12  # Important!
                ),
            ]
        )

        headset = self._create_rental_product(
            name='GS Headset', list_price=1., rental_price=75.,
            property_contract_template_id=contract_tmpl.id)
        oline_p = self._oline(headset)

        micro = self._create_rental_product(
            name='micro', list_price=3., rental_price=1.5,
            property_contract_template_id=False)
        oline_a = self._oline(micro)

        headset.accessory_product_ids |= micro

        so = self.env['sale.order'].create({
            'partner_id': partner.id, 'order_line': [oline_p, oline_a],
        })

        so.action_confirm()
        contracts = self.env['contract.contract'].of_sale(so)

        self.assertEqual(len(contracts), 1)
        self.assertEquals(
            [(l.name, l.quantity) for l in contracts.contract_line_ids],
            [('1 year of GS Headset', 1.0), ('1 month of micro', 12.0)])


class SaleOrderAttachmentsTC(RentalSaleOrderTC):

    def setUp(self):
        super(SaleOrderAttachmentsTC, self).setUp()
        self.partner = self.env.ref('base.res_partner_3')
        self.env['res.lang'].load_lang("fr_FR")
        self.env['res.lang'].pool.cache.clear()
        self.so = self.create_sale_order(self.partner)
        ct = self.so.mapped(
            "order_line.product_id.property_contract_template_id")[0]
        self.create_attachment("doc1_fr.txt", "fr_FR", ct)
        self.create_attachment("doc2_fr.txt", "fr_FR", ct)
        self.create_attachment("doc1_en.txt", "en_US", ct)
        self.create_attachment("doc_no_lang.txt", False, ct)
        # Remove report from default template to make it possible to add ours:
        self.env.ref("sale.email_template_edi_sale").report_template = False

    def create_attachment(self, name, lang, target_obj):
        return self.env['ir.attachment'].create({
            "name": name,
            "type": "binary",
            "datas": "toto",
            "res_model": target_obj._name,
            "res_id": target_obj.id,
            "lang": lang,
        })

    def check_sale_quotation_send_emails(self, lang):
        self.partner.lang = lang
        self.so.force_quotation_send()
        return sorted(self.so.message_ids[0].attachment_ids.mapped("name"))

    def test_sale_quotation_send_emails_fr(self):
        """ break /usr/lib/python3/dist-packages/odoo/models.py:1148 """
        self.assertEqual(
            self.check_sale_quotation_send_emails("fr_FR"),
            ["doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"])

    def test_sale_quotation_send_emails_en(self):
        self.assertEqual(
            self.check_sale_quotation_send_emails("en_US"),
            ["doc1_en.txt", "doc_no_lang.txt"])

    def test_sale_quotation_send_emails_no_lang(self):
        self.assertEqual(
            self.check_sale_quotation_send_emails(False),
            ["doc1_en.txt", "doc1_fr.txt", "doc2_fr.txt", "doc_no_lang.txt"])
