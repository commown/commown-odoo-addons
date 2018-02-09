import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class SCICSaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.depends('website_order_line.product_uom_qty',
                 'website_order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(
                order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(
                (not l.product_id.is_rental  # we need to ship the product
                 and l.product_id.type in ('service', 'digital'))
                for l in order.website_order_line
            )

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0,
                     attributes=None, **kwargs):
        """If given product is a crowd equity one, limit its quantity to 1.

        Note this does not enforce the quantity in the DB, which may
        be too much of a constraint. We just want people to know what
        they do when they buy an equity, is the spirit of the French
        Financial Markets Authority (AMF) rules.
        """
        result = super(SCICSaleOrder, self)._cart_update(
            product_id=product_id, line_id=line_id,
            add_qty=add_qty, set_qty=set_qty,
            attributes=attributes, **kwargs)
        product = self.env['product.product'].browse(product_id)
        if product.product_tmpl_id.is_crowd_equity() and result['quantity'] > 1:
            line = self.env['sale.order.line'].sudo().browse(result['line_id'])
            result['quantity'] = 1
            _logger.debug(
                'Forced quantity update of line %(l)s (product %(p)s) from'
                ' %(old_qty)s to %(new_qty)s',
                {'l': line.id,
                 'p': product.name,
                 'old_qty': line.product_uom_qty,
                 'new_qty': result['quantity']})
            line.update({'product_uom_qty': result['quantity']})
        return result
