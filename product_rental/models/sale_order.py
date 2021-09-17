import logging

from odoo import api, models, fields
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

    has_rental_product = fields.Boolean(
        'Has rental product', compute='_compute_has_rental', store=True)

    contract_count = fields.Integer(
        u'Related contract count', compute='_compute_contract_count')

    def _compute_contract_count(self):
        model = self.env['account.analytic.account']
        for sale in self:
            sale.contract_count = model.search_count([
                ('recurring_invoice_line_ids.sale_order_line_id.order_id',
                 '=', sale.id),
        ])

    @api.depends(
        'order_line',
        'order_line.product_uom_qty',
        'order_line.product_id.product_tmpl_id.is_rental',
    )
    def _compute_has_rental(self):
        for sale in self:
            sale.has_rental_product = any(
                l.product_id.product_tmpl_id.is_rental and l.product_uom_qty > 0
                for l in sale.order_line)

    @api.multi
    def has_rental(self):
        self.ensure_one()
        return self.has_rental_product

    @api.multi
    def contractual_documents(self):
        self.ensure_one()
        rcts = self.mapped('order_line.product_id.contract_template_id')
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'account.analytic.contract'),
            ('res_id', 'in', rcts.ids),
        ])

    @api.multi
    def action_quotation_send(self):
        self.ensure_one()
        email_act = super(ProductRentalSaleOrder, self).action_quotation_send()
        order_attachments = self.contractual_documents()
        if order_attachments:
            _logger.info(
                u'Prepare sending %s with %d attachment(s): %s',
                self.name, len(order_attachments),
                u', '.join([u"'%s'" % n
                            for n in order_attachments.mapped('name')]))
            ids = [att.id for att in sorted(order_attachments,
                                            key=lambda att: att.name)]
            email_act['context'].setdefault(
                'default_attachment_ids', []).append((6, 0, ids))
        return email_act

    def button_open_contracts(self):
        contracts = self.env['account.analytic.account'].search([
            ('recurring_invoice_line_ids.sale_order_line_id.order_id',
             'in', self.ids),
        ])
        result = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'domain': [('id', 'in', contracts.ids)],
            'name': _('Related contracts'),
            'context': {'is_contract': 1},
        }
        if len(contracts) == 1:  # single contract: display it directly
            view_types = ['form']
            result['res_id'] = contracts.id
        else:  # display a list
            view_types = ['list', 'form']
        view_xmlids = {
            'list': 'contract.view_account_analytic_account_journal_tree',
            'form': 'contract.account_analytic_account_recurring_form_form',
        }
        views = [self.env.ref(view_xmlids[t]) for t in view_types]
        result['views'] = [(v.id, v.type) for v in views]
        return result
