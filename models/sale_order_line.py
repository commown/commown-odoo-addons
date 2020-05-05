import logging
from collections import defaultdict

from odoo import api, models


_logger = logging.getLogger(__name__)


class ProductRentalSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_contract_vals(self):
        self.ensure_one()
        order = self.order_id
        index = self.env.context['contract_from_so']['index']
        data = super(ProductRentalSaleOrderLine, self)._prepare_contract_vals()
        data.update({
            'name': '%s-%02d' % (order.name, index),
            'is_auto_pay': False,
        })
        return data

    @api.multi
    def assign_contract_products(self):
        "Assign main product and accessories to n contracts per sale order line"

        bought_accessories = defaultdict(list)
        for l in self:
            accessory = l.product_id
            if accessory.is_rental and not accessory.is_contract:
                bought_accessories[l.product_id] += int(l.product_uom_qty) * [l]
        _logger.debug(u'%s: bought %d accessories', self[0].order_id.name,
                      sum(len(l) for l in bought_accessories.values()))

        contract_descrs = [
            {'so_line': so_line, 'main': so_line.product_id, 'accessories': []}
            for so_line in self.filtered('product_id.is_contract')
            for num in range(int(so_line.product_uom_qty))
        ]

        for contract_num, contract_descr in enumerate(contract_descrs, 1):
            _logger.debug(u'Examining so_line %s (contract %d)',
                          contract_descr['so_line'].name, contract_num)
            _logger.debug(
                u'Unassigned accessories: %s',
                u', '.join('%s (x%d)' % (a.name, len(so_lines))
                           for (a, so_lines) in bought_accessories.items()))
            for accessory, so_lines in bought_accessories.items():
                if accessory in contract_descr['main'].accessory_product_ids:
                    contract_descr['accessories'].append(
                        (accessory, so_lines.pop(0))
                    )
                    _logger.debug(u'> Assigned accessory %s', accessory.name)
                    if len(bought_accessories[accessory]) == 0:
                        del bought_accessories[accessory]

        _logger.debug(u'Accessories to be assigned to last contract (%d): %s',
                      len(contract_descrs),
                      u', '.join(
                          '%s (x%d)' % (a.name, len(so_lines))
                          for (a, so_lines) in bought_accessories.items())
                      or 'None')

        for accessory, so_lines in bought_accessories.items():
            contract_descrs[-1]['accessories'].extend([
                (accessory, so_line) for so_line in so_lines
            ])

        _logger.info(
            u'Contracts to be created for %s:\n%s', self[0].order_id.name,
            u'\n'.join(u'%d/ %s: %s' % (
                n, c['main'].name, u', '.join(
                    '%s (SO line %d)' % (product.name, so_line.id)
                    for (product, so_line) in c['accessories']))
                for n, c in enumerate(contract_descrs, 1)))

        return contract_descrs

    @api.multi
    def create_contract(self):
        """Create one contract per rented "main" *unitary* product (mind
        product qtty!) for all sale order lines.

        "Main" product are the one that are associated to a contract
        template. Main product accessories bought at the same time are
        added to the created contract lines using the ##ACCESSORY##
        marker feature described in the `_convert_contract_lines`
        method of the `account.analytic.account model`.

        This method should be called on confirmation of sale order.

        """

        contract_model = self.env['account.analytic.account']
        contract_descrs = self.assign_contract_products()

        for count, contract_descr in enumerate(contract_descrs, 1):
            so_line = contract_descr['so_line']
            _acs = contract_descr['accessories']
            acs = [(p, l, _acs.count((p, l))) for (p, l) in set(_acs)]

            _so_line = so_line.with_context({'contract_from_so': {
                'index': count,
                'main_product': so_line.product_id,
                'main_so_line': so_line,
                'accessories': sorted(acs, key=lambda a: a[0].id),
            }})

            contract = contract_model.create(_so_line._prepare_contract_vals())
            if not so_line.contract_id:  # Several contracts per so_line!
                so_line.contract_id = contract.id
