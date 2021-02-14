from datetime import datetime

from odoo import models, fields, api


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = [
        "crm.lead",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "team_id"

    so_line_id = fields.Many2one('sale.order.line', 'Ligne de commande')
    delivery_tracking = fields.Boolean(
        'Used for shipping', related='team_id.delivery_tracking')

    @api.multi
    def _default_shipping_parcel_type(self):
        return self.mapped('so_line_id.product_id.shipping_parcel_type_id')

    @api.multi
    def _attachment_from_label(self, name, meta_data, label_data):
        self.update({
            'expedition_ref': meta_data['labelResponse']['parcelNumber'],
            'expedition_date': datetime.today(),
            'delivery_date': False,
        })
        return super(CrmLead, self)._attachment_from_label(
            name, meta_data, label_data)

    @api.multi
    def parcel_labels(self, parcel_name=None, force_single=False):

        if parcel_name is not None:
            return super(CrmLead, self).parcel_labels(
                parcel_name, force_single=force_single)
        else:
            return self._print_parcel_labels(
                self._default_shipping_parcel_type(),
                force_single=force_single)
