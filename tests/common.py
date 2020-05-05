from odoo.tests.common import at_install, post_install, TransactionCase


@at_install(False)
@post_install(True)
class RentalSaleOrderTC(TransactionCase):

    def setUp(self):
        super(RentalSaleOrderTC, self).setUp()

        partner_portal = self.env.ref('portal.demo_user0_res_partner')
        self.user = partner_portal.user_ids.ensure_one()

        # Main rental products (with a rental contract template)
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1, recurring_invoice_line_ids=[
                self._invoice_line(
                    1, name='1 month Fairphone premium', specific_price=30.),
                self._invoice_line(2, name='1 month ##ACCESSORY##'),
                ])
        self.product1 = self._create_rental_product(
            1, name='Fairphone Premium', list_price=60., rental_price=30.,
            contract_template_id=contract_tmpl1.id)
        oline1 = self._oline(self.product1)

        contract_tmpl2 = self._create_rental_contract_tmpl(
            2, recurring_invoice_line_ids=[
                self._invoice_line(
                    2, '1 month of ##PRODUCT##', specific_price=0.0),
                self._invoice_line(3, '1 month of ##ACCESSORY##'),
                ])
        self.product2 = self._create_rental_product(
            2, name="PC", list_price=120., rental_price=60.,
            contract_template_id=contract_tmpl2.id)
        oline2 = self._oline(self.product2, product_uom_qty=2)

        # Accessory products
        product3 = self._create_rental_product(
            3, name='headset', list_price=3., rental_price=1.5,
            contract_template_id=False)
        oline3 = self._oline(product3)

        product4 = self._create_rental_product(
            4, name='screen', list_price=30., rental_price=15.,
            contract_template_id=False)
        oline4 = self._oline(product4, product_uom_qty=2)

        product5 = self._create_rental_product(
            5, name='keyboard', list_price=12., rental_price=6.,
            contract_template_id=False)
        oline5 = self._oline(product5)

        product6 = self._create_rental_product(
            6, name='keyboard deluxe', list_price=15., rental_price=7.5,
            contract_template_id=False)
        oline6 = self._oline(product6)

        self.product1.accessory_product_ids |= product3
        self.product2.accessory_product_ids |= product4 + product5 + product6

        self.so = self.env['sale.order'].create({
            'partner_id': partner_portal.id,
            'partner_invoice_id': partner_portal.id,
            'partner_shipping_id': partner_portal.id,
            'order_line': [oline1, oline2, oline3, oline4, oline5, oline6],
        })

    def _create_rental_product(self, num, **kwargs):
        kwargs.setdefault('name', 'product %d' % num)
        kwargs.setdefault('is_rental', True)
        kwargs.setdefault('type', 'service')
        if 'contract_template_id' not in kwargs:
            kwargs['contract_template_id'] = \
                self._create_rental_contract_tmpl(num).id
        kwargs['is_contract'] = bool(kwargs['contract_template_id'])
        return self.env['product.product'].create(kwargs)

    def _create_rental_contract_tmpl(self, num, **kwargs):
        kwargs.setdefault('recurring_rule_type', 'monthly')
        kwargs.setdefault('recurring_interval', 1)
        kwargs.setdefault('name', 'Test Contract Template %d' % num)
        return self.env['account.analytic.contract'].create(kwargs)

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

