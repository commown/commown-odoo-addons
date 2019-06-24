from .common import RentalSaleOrderTC


class SaleOrderTC(RentalSaleOrderTC):

    def test_add_rental_contract(self):
        """ Buying a rental product must add a rental contract """

        # Trigger the automatic action
        self.so.write({'state': 'sale'})

        # Check effects
        contracts = self.env['account.analytic.account'].search([
            ('partner_id', '=', self.so.partner_id.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
            ])
        self.assertEqual(len(contracts), 3)  # 1 FP, 2 computers

    def test_rental_contract_creation(self):
        """ Created rental contract has precise characteristics """

        self.so.write({'state': 'sale'})
        contracts = self.env['account.analytic.account'].search([
            ('name', 'ilike', '%' + self.so.name + '%'),
            ])
        self.assertEqual(len(contracts), 3)
        c1, c2, c3 = contracts

        ilines1 = c1.recurring_invoice_line_ids
        self.assertEqual(ilines1.mapped('name'),
                         ['1 month Fairphone premium', '1 month headset'])
        self.assertEqual(ilines1.mapped('price_unit'), [30., 1.5])

        ilines2 = c2.recurring_invoice_line_ids
        self.assertEqual(ilines2.mapped('name'), [
            '1 month of PC',
            '1 month of screen',
            '1 month of screen',
            '1 month of keyboard',
            '1 month of keyboard deluxe',
        ])
        self.assertEqual(ilines2.mapped('price_unit'),
                         [60.0, 15.0, 15.0, 6.0, 7.5])

        ilines3 = c3.recurring_invoice_line_ids
        self.assertEqual(ilines3.mapped('name'), ['1 month of PC'])
        # Global value will be 0 so that the sale_completion_check.py script
        # generates an error: we cannot associate accessories with the right
        # main rental product -> generate a wrong contract (with 0 amount).
        self.assertEqual(ilines3.mapped('price_unit'), [60.])
