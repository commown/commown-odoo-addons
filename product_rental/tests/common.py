from odoo.tests.common import SavepointCase


class RentalSaleOrderTC(SavepointCase):

    def get_default_tax(self, amount=20.0):
        return self.env['account.tax'].create({
            'amount': amount,
            'amount_type': 'percent',
            'price_include': True,  # french style
            'name': 'Default test tax',
            'type_tax_use': 'sale',
        })

    def create_sale_order(self, partner=None, tax=None):
        """Given tax (defaults to company's default) is used for contract
        products.
        """
        if partner is None:
            partner = self.env.ref('base.res_partner_3')
        if tax is None:
            tax = self.get_default_tax()
        # Main rental products (with a rental contract template)
        contract_tmpl1 = self._create_rental_contract_tmpl(
            1, contract_line_ids=[
                self._contract_line(1, '1 month Fairphone premium', tax,
                                   specific_price=25.),
                self._contract_line(2, '1 month ##ACCESSORY##', tax),
                ])
        product1 = self._create_rental_product(
            name='Fairphone Premium', list_price=60., rental_price=30.,
            property_contract_template_id=contract_tmpl1.id)
        oline_p1 = self._oline(product1)

        contract_tmpl2 = self._create_rental_contract_tmpl(
            2, contract_line_ids=[
                self._contract_line(
                    1, '1 month of ##PRODUCT##', tax, specific_price=0.0),
                self._contract_line(2, '1 month of ##ACCESSORY##', tax),
                ])
        product2 = self._create_rental_product(
            name="PC", list_price=130., rental_price=65.,
            property_contract_template_id=contract_tmpl2.id)
        oline_p2 = self._oline(product2, product_uom_qty=2,
                               price_unit=120)

        contract_tmpl3 = self._create_rental_contract_tmpl(
            3, contract_line_ids=[
                self._contract_line(
                    1, '1 month of ##PRODUCT##', tax, specific_price=0.0),
                ])
        product3 = self._create_rental_product(
            name="GS Headset", list_price=1., rental_price=10.,
            property_contract_template_id=contract_tmpl3.id, is_deposit=False)
        oline_p3 = self._oline(product3, product_uom_qty=1, price_unit=1.)

        contract_tmpl4 = self._create_rental_contract_tmpl(
            4, contract_line_ids=[
                self._contract_line(1, '1 month of ##PRODUCT##', tax,
                                   specific_price=0.0),
            ])
        product4 = self._create_rental_product(
            name="FP2", list_price=40., rental_price=20.,
            property_contract_template_id=contract_tmpl4.id)
        oline_p4 = self._oline(product4, product_uom_qty=1)

        # Accessory products
        a1 = self._create_rental_product(
            name='headset', list_price=3., rental_price=1.5,
            property_contract_template_id=False)
        oline_a1 = self._oline(a1)

        a2 = self._create_rental_product(
            name='screen', list_price=30., rental_price=15.,
            property_contract_template_id=False)
        oline_a2 = self._oline(a2, product_uom_qty=2)

        a3 = self._create_rental_product(
            name='keyboard', list_price=12., rental_price=6.,
            property_contract_template_id=False)
        oline_a3 = self._oline(a3, discount=10)

        a4 = self._create_rental_product(
            name='keyboard deluxe', list_price=15., rental_price=7.5,
            property_contract_template_id=False)
        oline_a4 = self._oline(a4)

        product1.accessory_product_ids |= a1
        product2.accessory_product_ids |= a2 + a3 + a4

        return self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [oline_p1, oline_p2, oline_p3, oline_p4,
                           oline_a1, oline_a2, oline_a3, oline_a4],
        })

    def _create_rental_product(self, name, **kwargs):
        kwargs['name'] = name
        kwargs.setdefault('is_rental', True)
        kwargs.setdefault('type', 'service')
        kwargs.setdefault('taxes_id', False)
        kwargs['is_contract'] = bool(kwargs['property_contract_template_id'])
        result = self.env['product.product'].create(kwargs)
        # Otherwise is_contract may be wrong (in one of commown_devices tests):
        result.env.cache.invalidate()
        return result

    def _create_rental_contract_tmpl(self, num, **kwargs):
        kwargs.setdefault('name', 'Test Contract Template %d' % num)
        return self.env['contract.template'].create(kwargs)

    def _oline(self, product, **kwargs):
        kwargs['product_id'] = product.id
        kwargs['product_uom'] = product.uom_id.id
        kwargs.setdefault('name', product.name)
        kwargs.setdefault('product_uom_qty', 1)
        kwargs.setdefault('price_unit', product.list_price)
        return (0, 0, kwargs)

    def _contract_line(self, num, name, product_tax=None, **kwargs):
        if 'product_id' not in kwargs:
            product = self.env['product.product'].create({
                'name': 'Contract product %d' % num, 'type': 'service'})
            if product_tax is not None:
                product.taxes_id = False
                product.taxes_id |= product_tax
            kwargs['product_id'] = product.id
            kwargs['uom_id'] = product.uom_id.id
        kwargs['name'] = name
        kwargs.setdefault('specific_price', 0.)
        kwargs.setdefault('quantity', 1)
        kwargs.setdefault('recurring_rule_type', 'monthly')
        kwargs.setdefault('recurring_interval', 1)
        kwargs.setdefault('commitment_duration', 12)
        return (0, 0, kwargs)
