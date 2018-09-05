from odoo import models, fields


class SaleAffiliate(models.Model):
    _inherit = 'sale.affiliate'

    restriction_product_tmpl_ids = fields.Many2many(
        'product.template', string='Restrict to products',
        help=('If not empty, only sales that contain at least one of these'
              ' products considered part of the affiliation.'),
        )

    def _is_sale_order_qualified(self, sale_order):
        """ Return a boolean telling if given sale order qualifies for
        the affiliation program, given the affiliate product restrictions,
        if any (otherwise, it will always qualify).
        When product restrictions apply, the method returns True if any of
        the order lines qualifies.
        """
        self.ensure_one()
        return not self.restriction_product_tmpl_ids or any(
            self._is_sale_order_line_qualified(ol)
            for ol in sale_order.order_line)

    def _is_sale_order_line_qualified(self, sale_order_line):
        """ Return a boolean telling if the give sale order line qualifies for
        the affiliation program, given the affiliate product restrictions,
        if any (otherwise, it will always qualify).
        """
        return not self.restriction_product_tmpl_ids or (
            sale_order_line.product_id.product_tmpl_id.id in [
                pt.id for pt in self.restriction_product_tmpl_ids])
