from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SaleOrderTC(TransactionCase):

    def setUp(self):
        super(SaleOrderTC, self).setUp()
        self.invest_manager = self.env['res.users'].create({
            'name': 'F W', 'login': 'fred@commown.fr', 'email': 'fc@test'})
        self.user = self.env['res.users'].create({
            'name': 'Flo C', 'login': 'fc', 'email': 'fc@test'})
        partner_portal = self.env['res.partner'].create({
            'name': 'Flo C', 'email': 'fc@test',
            'user_ids': [(6, 0, [self.user.id])]})
        self.g1 = self.env['res.groups'].create({'name': 'standard'})
        self.g2 = self.env['res.groups'].create({'name': 'premium'})
        self.g3 = self.env['res.groups'].create({'name': 'computer'})
        contract_tmpl1 = self.env['account.analytic.contract'].create({
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
            'name': 'Test Contract Template 1',
            })
        sales_team1 = self.env['crm.team'].create({
            'name': 'Test team1', 'use_leads': True,
        })
        product1 = self.env['product.product'].create({
            'name': 'fairphone rental', 'type': 'service',
            'is_rental': True, 'rental_contract_tmpl_id': contract_tmpl1.id,
            'followup_sales_team_id': sales_team1.id,
            })
        product1.product_tmpl_id.support_group_ids |= self.g1 + self.g2
        oline1 = (0, 0, {
            'name': product1.name, 'product_id': product1.id,
            'product_uom_qty': 1, 'product_uom': product1.uom_id.id,
            'price_unit': product1.list_price})
        contract_tmpl2 = self.env['account.analytic.contract'].create({
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
            'name': 'Test Contract Template 2',
            })
        sales_team2 = self.env['crm.team'].create({
            'name': 'Test team2', 'use_leads': True,
        })
        product2 = self.env['product.product'].create({
            'name': 'computer rental', 'type': 'service',
            'is_rental': True, 'rental_contract_tmpl_id': contract_tmpl2.id,
            'followup_sales_team_id': sales_team2.id,
            })
        product2.product_tmpl_id.support_group_ids |= self.g3
        oline2 = (0, 0, {
            'name': product2.name, 'product_id': product2.id,
            'product_uom_qty': 1, 'product_uom': product2.uom_id.id,
            'price_unit': product2.list_price})
        product3 = self.env['product.product'].create({
            'name': 'keyboard rental', 'type': 'service', 'is_rental': True,
            })
        oline3 = (0, 0, {
            'name': product3.name, 'product_id': product3.id,
            'product_uom_qty': 1, 'product_uom': product3.uom_id.id,
            'price_unit': product3.list_price})
        self.so = self.env['sale.order'].create({
            'partner_id': partner_portal.id,
            'partner_invoice_id': partner_portal.id,
            'partner_shipping_id': partner_portal.id,
            'order_line': [oline1, oline2, oline3],
        })

    def test_add_to_support_groups_action(self):
        """ Add to support group action on a sale order must add the buyer to
        the sale's support groups.
        """
        # Check test prerequisites
        self.assertFalse(self.user.groups_id & (self.g1 | self.g2))
        # Run the action
        context = {'active_model': 'sale.order', 'active_id': self.so.id}
        action = self.env.ref('commown.action_add_to_support_groups')
        action.with_context(context).run()
        # Check action effects
        self.assertIn(self.g1, self.user.groups_id)
        self.assertIn(self.g2, self.user.groups_id)

    def test_buyer_automatic_actions(self):
        """ Buying a product must trigger automatic actions, check some:
        - add buyer to product's support groups
        - add a rental followup card
        - add a specific receivable account for the buyer
        - add a rental contract
        """
        # Check test prerequisites
        self.assertFalse(self.user.groups_id & (self.g1 | self.g2 | self.g3))
        # Trigger the automatic action
        self.so.write({'state': 'sent'})
        #
        # Check effects:

        # - support groups
        self.assertIn(self.g1, self.user.groups_id)
        self.assertIn(self.g2, self.user.groups_id)
        self.assertIn(self.g3, self.user.groups_id)

        # - followup card
        partner = self.so.partner_id
        products = [l.product_id for l in self.so.order_line]
        leads = self.env['crm.lead'].search([
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
        ])
        self.assertEqual(len(leads), 2)
        self.assertItemsEqual([l.team_id for l in leads],
                              [p.followup_sales_team_id
                               for p in products if p.followup_sales_team_id])

        # - receivable account
        self.assertEqual(partner.property_account_receivable_id.name,
                         partner.name)

        # - rental contracts
        contracts = self.env['account.analytic.account'].search([
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
            ])
        self.assertEqual(len(contracts), 2)
        self.assertItemsEqual([c.contract_template_id for c in contracts],
                              [p.rental_contract_tmpl_id
                               for p in products if p.rental_contract_tmpl_id])
