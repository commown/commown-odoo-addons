import logging
from collections import defaultdict

from odoo import api, models


_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def has_rental(self):
        _logger.warning('has_rental is now obsolete, please use is_contract')
        self.ensure_one()
        return self.is_contract

    @api.multi
    def contractual_documents(self):
        self.ensure_one()
        rcts = self.mapped(
            'order_line.product_id.property_contract_template_id')
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'contract.template'),
            ('res_id', 'in', rcts.ids),
        ])

    @api.multi
    def action_quotation_send(self):
        "Add contractual documents to the quotation email"
        self.ensure_one()
        email_act = super().action_quotation_send()
        order_attachments = self.contractual_documents()
        if order_attachments:
            _logger.info(
                'Prepare sending %s with %d attachment(s): %s',
                self.name, len(order_attachments),
                ', '.join(["'%s'" % n
                           for n in order_attachments.mapped('name')]))
            ids = [att.id for att in sorted(order_attachments,
                                            key=lambda att: att.name)]
            email_act['context'].setdefault(
                'default_attachment_ids', []).append((6, 0, ids))
        return email_act

    @api.multi
    def assign_accessories(self):
        "Assign accessories to contract sale order lines"

        bought_accessories = defaultdict(list)
        for so_line in self.order_line:
            accessory, qty = so_line.product_id, so_line.product_uom_qty
            if accessory.is_rental and not accessory.is_contract:
                bought_accessories[accessory] += int(qty) * [so_line]

        _logger.debug('%s: bought %d accessories', self.name,
                      sum(len(lines) for lines in bought_accessories.values()))

        acc_by_so_line = {
            so_line: []
            for so_line in self.order_line.filtered('product_id.is_contract')
        }

        for so_line_num, so_line in enumerate(acc_by_so_line, 1):
            _logger.debug('Examining so_line %s (num %d)',
                          so_line.name, so_line_num)
            _logger.debug(
                'Unassigned accessories: %s',
                ', '.join('%s (x%d)' % (a.name, len(so_lines))
                          for (a, so_lines) in bought_accessories.items()))
            main_product = so_line.product_id
            for accessory, acc_so_lines in list(bought_accessories.items()):
                if accessory in main_product.accessory_product_ids:
                    qty = int(min(so_line.product_uom_qty, len(acc_so_lines)))
                    remain_qty = len(acc_so_lines) - qty
                    acc_by_so_line[so_line].extend(
                        zip(accessory, acc_so_lines[remain_qty:]))
                    acc_so_lines[remain_qty:] = []
                    _logger.debug('> Assigned accessory %s x%d',
                                  accessory.name, qty)
                    if len(bought_accessories[accessory]) == 0:
                        del bought_accessories[accessory]

        _logger.debug('Accessories to be assigned to last contract (%d): %s',
                      len(acc_by_so_line),
                      ', '.join(
                          '%s (x%d)' % (a.name, len(so_lines))
                          for (a, so_lines) in bought_accessories.items())
                      or 'None')

        if acc_by_so_line:
            for accessory, so_lines in bought_accessories.items():
                acc_by_so_line[-1]['accessories'].extend([
                    (accessory, so_line) for so_line in so_lines
                ])

        _logger.info(
            'Contracts to be created for %s:\n%s', self.name,
            '\n'.join('%d/ %s: %s' % (
                n, so_line.product_id.name, ', '.join(
                    '%s (SO line %d)' % (product.name, acc_so_line.id)
                    for (product, acc_so_line) in acc_by_so_line[so_line]))
                for n, so_line in enumerate(acc_by_so_line, 1)))

        return acc_by_so_line

    @api.multi
    def _prepare_contract_value(self, contract_template):
        " Don't set is_auto_pay: the contract does not start immediately "
        self.ensure_one()
        data = super()._prepare_contract_value(contract_template)
        data['is_auto_pay'] = False
        return data

    @api.multi
    def action_create_contract(self):
        self.ensure_one()
        acc_by_so_line = self.assign_accessories()
        return super(
            ProductRentalSaleOrder,
            self.with_context(product_rental_acc_by_so_line=acc_by_so_line)
        ).action_create_contract()
