from odoo.tests.common import TransactionCase


class SaleOrderTC(TransactionCase):

    def setUp(self):
        super(SaleOrderTC, self).setUp()
        user_portal = self.env['res.users'].create({
            'name': 'Flo C', 'login': 'fc', 'email': 'fc@test'})
        partner_portal = self.env['res.partner'].create({
            'name': 'Flo C', 'email': 'fc@test',
            'user_ids': [(6, 0, [user_portal.id])]})
        product = self.env['product.product'].create({
            'name': 'fairphone rental', 'type': 'service',
        })
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
        # Add supported groups to the sold product
        g1 = self.env['res.groups'].create({'name': 'standard'})
        g2 = self.env['res.groups'].create({'name': 'premium'})
        self.so.product_id.product_tmpl_id.support_group_ids |= g1 + g2
        # Check test prerequisites
        user = self.so.partner_id.user_ids
        self.assertNotIn(g1, user.groups_id)
        self.assertNotIn(g2, user.groups_id)
        # Run the action
        context = {'active_model': 'sale.order', 'active_id': self.so.id}
        action = self.env.ref('commown.action_add_to_support_groups')
        action.with_context(context).run()
        # Check action effects
        self.assertIn(g1, user.groups_id)
        self.assertIn(g2, user.groups_id)
