from datetime import date

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

    def generate_contract_invoices(self, partner=None, tax=None):
        so = self.create_sale_order(partner, tax)
        so.action_confirm()
        contracts = self.env['contract.contract'].search([
            ('name', 'ilike', '%' + so.name + '%'),
            ])
        lines = contracts.mapped('contract_line_ids')
        self.assertEqual(set(lines.mapped('date_start')), {date(2030, 1, 1)})
        return contracts._recurring_create_invoice()

    def test_rental_contract_creation_without_fpos(self):
        """Contracts generated from rental sales have specific characteristics

        We use tax-included in the price for tests (french
        style). Company's default tax is used for products without a
        specific tax (see sale.order.line `compute_rental_price` method doc)

        """
        i1, i2, i3, i4, i5 = invs = self.generate_contract_invoices(
            tax=self.new_tax(20.0))
        c1, c2, c3, c4, c5 = invs.mapped(
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

        i1, i2, i3, i4, i5 = invs = self.generate_contract_invoices(
            partner, tax_src)
        c1, c2, c3, c4, c5 = invs.mapped(
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
