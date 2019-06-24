from odoo.addons.product_rental.tests.common import RentalSaleOrderTC
from .common import MockedEmptySessionMixin


class SaleOrderTC(MockedEmptySessionMixin, RentalSaleOrderTC):


    def setUp(self):
        super(SaleOrderTC, self).setUp()

        self.g1 = self.env['res.groups'].create({'name': 'standard'})
        self.g2 = self.env['res.groups'].create({'name': 'premium'})
        self.g3 = self.env['res.groups'].create({'name': 'computer'})

        self.product1.product_tmpl_id.support_group_ids |= self.g1 + self.g2
        self.product2.product_tmpl_id.support_group_ids |= self.g3

        self.product1.followup_sales_team_id = self._create_sales_team(1).id
        self.product2.followup_sales_team_id = self._create_sales_team(3).id

    def _create_sales_team(self, num, **kwargs):
        kwargs.setdefault('name', 'Test team%d' % num)
        kwargs.setdefault('use_leads', True)
        team = self.env['crm.team'].create(kwargs)
        for n in range(4):
            self.env['crm.stage'].create({
                'team_id': team.id,
                'name': u'test %d' % n if n != 1 else u'test [stage: start]'})
        return team

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

    def test_add_to_product_support_group(self):
        """ Buying a product must add buyer to product's support groups """

        # Check test prerequisites
        self.assertFalse(self.user.groups_id & (self.g1 | self.g2 | self.g3))

        # Trigger the automatic action
        self.so.write({'state': 'sale'})

        # Check effects
        self.assertIn(self.g1, self.user.groups_id)
        self.assertIn(self.g2, self.user.groups_id)
        self.assertIn(self.g3, self.user.groups_id)

    def test_add_followup_card_without_coupon(self):
        """ Buying a rental product must add a rental followup card """

        # Trigger the automatic action
        self.so.write({'state': 'sale'})

        # Check effects
        partner = self.so.partner_id
        products = [l.product_id for l in self.so.order_line]
        leads = self.env['crm.lead'].search([
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
        ])
        self.assertEqual(len(leads), 3)
        self.assertEqual(
            sorted(l.name.split(' ', 1)[0] for l in leads),
            ["[%s-%02d]" % (self.so.name, i) for i in range(1, 4)])
        self.assertEqual(sorted(l.so_line_id.product_id.name for l in leads),
                         ['Fairphone Premium', 'PC', 'PC'])
        self.assertEqual(set([l.team_id for l in leads]),
                         set([p.followup_sales_team_id
                              for p in products if p.followup_sales_team_id]))
        self.assertTrue(all('coupon' not in name.lower()
                            for name in leads.mapped('name')))

    def test_add_followup_card_name_with_coupon(self):
        """ Followup card name must indicate sale coupons were used if any """

        # Simulate the usage of a coupon in the sale:
        campaign = self.env['coupon.campaign'].create({
            'name': u'Test campaign',
            'seller_id': self.env.ref('base.res_partner_1').id,
        })
        self.env['coupon.coupon'].create({
            'used_for_sale_id': self.so.id,
            'campaign_id': campaign.id,
        })

        # Trigger the automatic action
        self.so.write({'state': 'sale'})

        # Check effects
        partner = self.so.partner_id
        leads = self.env['crm.lead'].search([
            ('partner_id', '=', partner.id),
            ('name', 'ilike', '%' + self.so.name + '%'),
        ])
        self.assertEqual(len(leads), 3)
        self.assertTrue(all('coupon' in name.lower()
                            for name in leads.mapped('name')))

    def test_add_receivable_account(self):
        " Buying a product must add the buyer a dedicated receivable account "

        # Trigger the automatic action
        self.so.write({'state': 'sale'})

        # Check effects
        partner = self.so.partner_id
        self.assertEqual(partner.property_account_receivable_id.name,
                         partner.name)
