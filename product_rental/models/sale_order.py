import logging
from collections import defaultdict

from odoo import api, models


_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

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
    def assign_contract_products(self):
        "Assign main product and accessories to n contracts per sale order line"

        bought_accessories = defaultdict(list)
        for l in self.order_line:
            accessory = l.product_id
            if accessory.is_rental and not accessory.is_contract:
                bought_accessories[l.product_id] += int(l.product_uom_qty) * [l]
        _logger.debug(u'%s: bought %d accessories', self.name,
                      sum(len(l) for l in bought_accessories.values()))

        contract_descrs = [
            {'so_line': so_line, 'main': so_line.product_id, 'accessories': []}
            for so_line in self.order_line.filtered('product_id.is_contract')
            for num in range(int(so_line.product_uom_qty))
        ]

        for contract_num, contract_descr in enumerate(contract_descrs, 1):
            _logger.debug(u'Examining so_line %s (contract %d)',
                          contract_descr['so_line'].name, contract_num)
            _logger.debug(
                u'Unassigned accessories: %s',
                u', '.join('%s (x%d)' % (a.name, len(so_lines))
                           for (a, so_lines) in bought_accessories.items()))
            for accessory, so_lines in list(bought_accessories.items()):
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

        if contract_descrs:
            for accessory, so_lines in bought_accessories.items():
                contract_descrs[-1]['accessories'].extend([
                    (accessory, so_line) for so_line in so_lines
                ])

        _logger.info(
            u'Contracts to be created for %s:\n%s', self.name,
            u'\n'.join(u'%d/ %s: %s' % (
                n, c['main'].name, u', '.join(
                    '%s (SO line %d)' % (product.name, so_line.id)
                    for (product, so_line) in c['accessories']))
                for n, c in enumerate(contract_descrs, 1)))

        return contract_descrs

    @api.multi
    def _create_rental_contract(self, contract_template, num):
        self.ensure_one()
        values = self._prepare_contract_value(contract_template)
        values.update({
            'is_auto_pay': False,
            'name': "%s-%02d" % (self.name, num),
        })
        contract = self.env['contract.contract'].create(values)
        contract._onchange_contract_template_id()
        contract._onchange_contract_type()
        return contract

    @api.multi
    def action_create_contract(self):
        contracts = self.env['contract.contract']
        contract_descrs = self.assign_contract_products()
        order_line_model = self.env['sale.order.line']

        for count, contract_descr in enumerate(contract_descrs, 1):
            ctemplate = contract_descr['main'].with_context(
                force_company=self.company_id.id
            ).property_contract_template_id
            contract = self._create_rental_contract(ctemplate, count)
            contracts |= contract
            clines = order_line_model._product_rental_create_contract_line(
                contract, contract_descr)

        return contracts
