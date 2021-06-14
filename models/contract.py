import logging

from odoo import models, fields


_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "account.analytic.account"

    picking_ids = fields.One2many(
        'stock.picking',
        'contract_id',
        string=u'Pickings')

    def send_all_picking(self):
        products = self.recurring_invoice_line_ids.mapped(
            'sale_order_line_id.product_id.product_tmpl_id.stockable_product_id'
        )

        if not products:
            _logger.warning('Empty initial picking for contract %s', self.name)
            return None
        elif len(products) > 1:
            _logger.warning('More than 1 product to deliver for %s', self.name)
            return None

        # XXX hardcoded
        picking_type = self.env.ref('stock.picking_type_internal')
        orig_location = self.env.ref('stock.stock_location_stock')

        # XXX incorrect partner for B2B:
        dest_location = self.partner_id.set_customer_location()

        picking_data = {
            'move_type': 'direct',
            'picking_type_id': picking_type.id,
            'location_id': orig_location.id,
            'location_dest_id': dest_location.id,
            'min_date': fields.Date.today(),
            'origin': self.name,
            'move_lines': [
                (0, 0, {
                    'name': '/',
                    'picking_type_id': picking_type.id,
                    'location_id': orig_location.id,
                    'location_dest_id': dest_location.id,
                    'product_id': products.id,
                    'product_uom_qty': 1,  # XXX hardcoded
                    'product_uom': self.env.ref('product.product_uom_unit').id,
                })
            ],
        }

        picking = self.env['stock.picking'].create(picking_data)
        picking.action_confirm()
        picking.action_assign()
        self.picking_ids |= picking

        return picking
