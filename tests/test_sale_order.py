from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class SaleOrderTC(TransactionCase):

    def setUp(self):
        super(SaleOrderTC, self).setUp()
        self.user = self.env['res.users'].create({
            'name': 'Flo C', 'login': 'fc', 'email': 'fc@test'})
        partner_portal = self.env['res.partner'].create({
            'name': 'Flo C', 'email': 'fc@test',
            'user_ids': [(6, 0, [self.user.id])]})
        self.g1 = self.env['res.groups'].create({'name': 'standard'})
        self.g2 = self.env['res.groups'].create({'name': 'premium'})
        product = self.env['product.product'].create({
            'name': 'fairphone rental', 'type': 'service',
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

    def test_add_buyer_to_product_support_groups_ar(self):
        # Check test prerequisites
        self.assertFalse(self.user.groups_id & (self.g1 | self.g2))
        # Trigger the automatic action
        self.so.write({'state': 'sent'})
        # Check action effects
        self.assertIn(self.g1, self.user.groups_id)
        self.assertIn(self.g2, self.user.groups_id)
