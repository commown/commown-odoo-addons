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
        contract_template = self.env['account.analytic.contract'].create({
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
            'name': 'Test Contract Template',
            })
        product = self.env['product.product'].create({
            'name': 'fairphone rental', 'type': 'service',
            'is_rental': True, 'rental_contract_tmpl_id': contract_template.id,
            })
        product.product_tmpl_id.support_group_ids |= self.g1 + self.g2
        oline = (0, 0, {
            'name': product.name, 'product_id': product.id,
            'product_uom_qty': 1, 'product_uom': product.uom_id.id,
            'price_unit': product.list_price})
        self.so = self.env['sale.order'].create({
            'partner_id': partner_portal.id,
            'partner_invoice_id': partner_portal.id,
            'partner_shipping_id': partner_portal.id,
            'order_line': [oline],
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
        self.assertFalse(self.user.groups_id & (self.g1 | self.g2))
        # Trigger the automatic action
        self.so.write({'state': 'sent'})
        #
        # Check effects:
        #
        # - support groups
        self.assertIn(self.g1, self.user.groups_id)
        self.assertIn(self.g2, self.user.groups_id)
        # - followup card
        sales_team_id = self.env.ref('sales_team.salesteam_website_sales').id
        partner = self.so.partner_id
        leads = self.env['crm.lead'].search([
            ('team_id', '=', sales_team_id),
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
        ])
        self.assertEqual(len(leads), 1)
        # - receivable account
        self.assertEqual(partner.property_account_receivable_id.name,
                         partner.name)
        # - rental contract
        product = self.so.product_id
        contracts = self.env['account.analytic.account'].search([
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
            ('contract_template_id', '=', product.rental_contract_tmpl_id.id),
        ])
        self.assertEqual(len(contracts), 1)
