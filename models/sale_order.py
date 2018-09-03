from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        """Reset current sales' affiliate request to False if the affiliate
        has a product restriction that is not compatible with the sold
        products.
        """
        so = super(SaleOrder, self).create(vals)
        if so.affiliate_request_id:
            affiliate = so.affiliate_request_id.affiliate_id
            restriction_product_tmpl_ids = set(
                p.id for p in affiliate.restriction_product_tmpl_ids)
            if restriction_product_tmpl_ids:
                sold_product_ids = set(ol.product_id.product_tmpl_id.id
                                       for ol in so.order_line)
                if not (restriction_product_tmpl_ids & sold_product_ids):
                    so.affiliate_request_id = False
        return so
