from .common import RentalSaleOrderTC


class SaleOrderTC(RentalSaleOrderTC):

    def test_rental_contract_creation(self):
        """ Created rental contract has precise characteristics """

        self.so.action_confirm()
        so_lines = self.so.order_line

        contracts = self.env['account.analytic.account'].search([
            ('name', 'ilike', '%' + self.so.name + '%'),
            ])

        sale_monthly_amount = sum(
            l.price_unit * l.quantity
            for c in contracts
            for l in c.recurring_invoice_line_ids)
        #self.assertEqual(sale_monthly_amount, 195)

        self.assertEqual(len(contracts), 3)
        c1, c2, c3 = contracts

        ilines1 = c1.recurring_invoice_line_ids
        self.assertEqual(ilines1.mapped('name'),
                         ['1 month Fairphone premium', '1 month headset'])
        self.assertEqual(ilines1.mapped('price_unit'), [30., 1.5])
        self.assertEqual(ilines1.mapped('quantity'), [1, 1])
        self.assertEqual(ilines1.mapped('sale_order_line_id.product_id.name'),
                         ['Fairphone Premium', 'headset'])

        ilines2 = c2.recurring_invoice_line_ids
        self.assertEqual(ilines2.mapped('name'), [
            u'1 month of PC',
            u'1 month of screen',
            u'1 month of keyboard',
            u'1 month of keyboard deluxe',
        ])
        self.assertEqual(ilines2.mapped('price_unit'), [60., 15., 6.0, 7.5])
        self.assertEqual(ilines2.mapped('quantity'), [1, 1, 1, 1])
        self.assertEqual(ilines2.mapped('sale_order_line_id.product_id.name'),
                         [u'PC', u'screen', u'keyboard', u'keyboard deluxe'])

        ilines3 = c3.recurring_invoice_line_ids
        self.assertEqual(ilines3.mapped('name'),
                         [u'1 month of PC', u'1 month of screen'])
        self.assertEqual(ilines3.mapped('price_unit'), [60., 15.])
        self.assertEqual(ilines3.mapped('quantity'), [1, 1])
        self.assertEqual(ilines3.mapped('sale_order_line_id.product_id.name'),
                         [u'PC', u'screen'])
