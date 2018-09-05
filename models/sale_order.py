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
            if not affiliate._is_sale_order_qualified(so):
                so.affiliate_request_id = False
        return so
