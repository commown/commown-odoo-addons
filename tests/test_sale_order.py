from odoo.tests.common import at_install, post_install
from . import common


@at_install(False)
@post_install(True)
class SaleOrderTC(common.MockedEmptySessionTC):

    def setUp(self):
        super(SaleOrderTC, self).setUp()

        User = self.env['res.users']
        Group = self.env['res.groups']
        Partner = self.env['res.partner']

        self.invest_manager = User.create({
            'name': 'F W', 'login': 'fred@commown.fr', 'email': 'fc@test'})
        self.user = User.create({
            'name': 'Flo C', 'login': 'fc', 'email': 'fc@test'})
        partner_portal = Partner.create({
            'name': 'Flo C', 'email': 'fc@test',
            'user_ids': [(6, 0, [self.user.id])]})

        self.g1 = Group.create({'name': 'standard'})
        self.g2 = Group.create({'name': 'premium'})
        self.g3 = Group.create({'name': 'computer'})

        # Main rental products (with a rental contract template)
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(
                    1, name='1 month Fairphone premium', specific_price=30.),
                self._invoice_line(2, name='1 month ##ACCESSORY##'),
                ])
        product1 = self._create_rental_product(
            1, name='Fairphone Premium', sgroups=self.g1+self.g2,
            list_price=60., rental_contract_tmpl_id=contract_tmpl1.id)
        oline1 = self._oline(product1)

        contract_tmpl2 = self._create_rental_contract_tmpl(
            2, recurring_invoice_line_ids=[
                self._invoice_line(
                    2, '1 month of ##PRODUCT##', specific_price=0.0),
                self._invoice_line(3, '1 month of ##ACCESSORY##'),
                ])
        product2 = self._create_rental_product(
            2, self.g3, name="PC", list_price=120.,
            rental_contract_tmpl_id=contract_tmpl2.id)
        oline2 = self._oline(product2, product_uom_qty=2)

        # Accessory products
        product3 = self._create_rental_product(
            3, name='headset', list_price=3.,
            followup_sales_team_id=False, rental_contract_tmpl_id=False)
        oline3 = self._oline(product3)

        product4 = self._create_rental_product(
            4, name='screen', list_price=30.,
            followup_sales_team_id=False, rental_contract_tmpl_id=False)
        oline4 = self._oline(product4, product_uom_qty=2)

        product5 = self._create_rental_product(
            5, name='keyboard', list_price=12.,
            followup_sales_team_id=False, rental_contract_tmpl_id=False)
        oline5 = self._oline(product5)

        product6 = self._create_rental_product(
            6, name='keyboard deluxe', list_price=15.,
            followup_sales_team_id=False, rental_contract_tmpl_id=False)
        oline6 = self._oline(product6)

        product1.accessory_product_ids |= product3
        product2.accessory_product_ids |= product4 + product5 + product6

        self.so = self.env['sale.order'].create({
            'partner_id': partner_portal.id,
            'partner_invoice_id': partner_portal.id,
            'partner_shipping_id': partner_portal.id,
            'order_line': [oline1, oline2, oline3, oline4, oline5, oline6],
        })

    def _create_rental_product(self, num, sgroups=None, **kwargs):
        kwargs.setdefault('name', 'product %d' % num)
        kwargs.setdefault('is_rental', True)
        kwargs.setdefault('type', 'service')
        if 'followup_sales_team_id' not in kwargs:
            kwargs['followup_sales_team_id'] = self._create_sales_team(num).id
        if 'rental_contract_tmpl_id' not in kwargs:
            kwargs['rental_contract_tmpl_id'] = \
                self._create_rental_contract_tmpl(num).id
        product = self.env['product.product'].create(kwargs)
        if sgroups is not None:
            product.product_tmpl_id.support_group_ids |= sgroups
        return product

    def _create_rental_contract_tmpl(self, num, **kwargs):
        kwargs.setdefault('recurring_rule_type', 'monthly')
        kwargs.setdefault('recurring_interval', 1)
        kwargs.setdefault('name', 'Test Contract Template %d' % num)
        return self.env['account.analytic.contract'].create(kwargs)

    def _create_sales_team(self, num, **kwargs):
        kwargs.setdefault('name', 'Test team%d' % num)
        kwargs.setdefault('use_leads', True)
        team = self.env['crm.team'].create(kwargs)
        for n in range(4):
            self.env['crm.stage'].create({
                'team_id': team.id,
                'name': u'test %d' % n if n != 1 else u'test [stage: start]'})
        return team

    def _oline(self, product, **kwargs):
        kwargs['product_id'] = product.id
        kwargs['product_uom'] = product.uom_id.id
        kwargs.setdefault('name', product.name)
        kwargs.setdefault('product_uom_qty', 1)
        kwargs.setdefault('price_unit', product.list_price)
        return (0, 0, kwargs)

    def _invoice_line(self, num, name, **kwargs):
        if 'product_id' not in kwargs:
            product = self.env['product.product'].create({
                'name': 'Line product %d' % num, 'type': 'service'})
            kwargs['product_id'] = product.id
            kwargs['uom_id'] = product.uom_id.id
        kwargs['name'] = name
        kwargs.setdefault('specific_price', 0.)
        kwargs.setdefault('quantity', 1)
        return (0, 0, kwargs)

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
        self.assertEqual(ilines1.mapped('price_unit'), [30., 1.25])

        ilines2 = c2.recurring_invoice_line_ids
        self.assertEqual(ilines2.mapped('name'), [
            '1 month of PC',
            '1 month of screen',
            '1 month of screen',
            '1 month of keyboard',
            '1 month of keyboard deluxe',
        ])
        self.assertEqual(ilines2.mapped('price_unit'),
                         [50.0, 12.5, 12.5, 5.0, 6.25])

        ilines3 = c3.recurring_invoice_line_ids
        self.assertEqual(ilines3.mapped('name'), ['1 month of PC'])
        # Global value will be 0 so that the sale_completion_check.py script
        # generates an error: we cannot associate accessories with the right
        # main rental product -> generate a wrong contract (with 0 amount).
        self.assertEqual(ilines3.mapped('price_unit'), [50.])
