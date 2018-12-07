import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def has_rental(self):
        self.ensure_one()
        return any(line.product_id.product_tmpl_id.is_rental
                   for line in self.order_line)

    @api.multi
    def contractual_documents(self):
        self.ensure_one()
        rcts = self.mapped('order_line.product_id.rental_contract_tmpl_id')
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
            ids = [att.id for att in sorted(order_attachments,
                                            key=lambda att: att.name)]
            email_act['context'].setdefault(
                'default_attachment_ids', []).append((6, 0, ids))
        return email_act
