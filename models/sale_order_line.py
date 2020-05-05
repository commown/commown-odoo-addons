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
        index = self.env.context['so_line_contract']['index']
        data = super(ProductRentalSaleOrderLine, self)._prepare_contract_vals()
        data.update({
            'name': '%s-%02d' % (order.name, index),
            'is_auto_pay': False,
        })
        return data

    @api.multi
    def assign_contract_products(self):
        "Assign main product and accessories to n contracts per sale order line"

        bought_accessories = defaultdict(int)
        for l in self:
            accessory = l.product_id
            if accessory.is_rental and not accessory.is_contract:
                bought_accessories[l.product_id] += int(l.product_uom_qty)
        _logger.debug(u'%s: bought %d accessories', self[0].order_id.name,
                      sum(bought_accessories.values()))

        contract_descrs = [
            {'so_line': so_line, 'main': so_line.product_id, 'accessories': []}
            for so_line in self.filtered('product_id.is_contract')
            for num in range(int(so_line.product_uom_qty))
        ]

        for contract_num, contract_descr in enumerate(contract_descrs, 1):
            _logger.debug(u'Examining so_line %s (contract %d)',
                          contract_descr['so_line'].name, contract_num)
            _logger.debug(u'Unassigned accessories: %s',
                          u', '.join('%s (x%d)' % (a.name, num)
                                     for (a, num) in bought_accessories.items()))
            for accessory, unassigned_num in bought_accessories.items():
                if accessory in contract_descr['main'].accessory_product_ids:
                    contract_descr['accessories'].append(accessory)
                    _logger.debug(u'> Assigned accessory %s', accessory.name)
                    bought_accessories[accessory] -= 1
                    if bought_accessories[accessory] == 0:
                        del bought_accessories[accessory]

        _logger.debug(u'Accessories to be assigned to last contract (%d): %s',
                      len(contract_descrs),
                      u', '.join(
                          '%s (x%d)' % (a.name, num)
                          for (a, num) in bought_accessories.items()) or 'None')

        for accessory, unassigned_num in bought_accessories.items():
            contract_descrs[-1]['accessories'].extend(
                [accessory] * unassigned_num)

        _logger.info(
            u'Contracts to be created for %s:\n%s', self[0].order_id.name,
            u'\n'.join(u'%d/ %s: %s' % (
                n, c['main'].name, u', '.join(
                    '%s (x%d)' % (a.name, num) for a in c['accessories']))
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

            _so_line = so_line.with_context({'so_line_contract': {
                'index': count,
                'main_product': so_line.product_id,
                'accessories': sorted([(a, _acs.count(a)) for a in set(_acs)],
                                      key=lambda (a, n): a.id),
            }})

            contract = contract_model.create(_so_line._prepare_contract_vals())
            if not so_line.contract_id:  # Several contracts per so_line!
                so_line.contract_id = contract.id
