from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = [
        "crm.lead",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "team_id"
    _delivery_tracking_stage_parent_rel = "team_id"

    so_line_id = fields.Many2one("sale.order.line", "Ligne de commande")
    delivery_tracking = fields.Boolean(
        "Delivery tracking", related="team_id.delivery_tracking"
    )

    @api.multi
    def _default_shipping_parcel_type(self):
        return self.mapped("so_line_id.product_id.shipping_parcel_type_id")

    @api.multi
    def _attachment_from_label(self, name, meta_data, label_data):
        self.update(
            {
                "expedition_ref": meta_data["labelResponse"]["parcelNumber"],
                "expedition_date": date.today(),
                "delivery_date": False,
            }
        )
        return super(CrmLead, self)._attachment_from_label(name, meta_data, label_data)

    @api.multi
    def parcel_labels(self, parcel_name=None, force_single=False):

        if parcel_name is not None:
            return super(CrmLead, self).parcel_labels(
                parcel_name, force_single=force_single
            )
        else:
            return self._print_parcel_labels(
                self._default_shipping_parcel_type(), force_single=force_single
            )

    def _recipient_partner(self):
        "Override recipient partner computation to use the sale.order if any"
        self.ensure_one()

        if self.recipient_partner_id:
            return self.recipient_partner_id

        so_address = self.mapped("so_line_id.order_id.partner_shipping_id")
        odoo_address = self.env["res.partner"].browse(
            self.partner_id.address_get(["delivery"])["delivery"]
        )

        if so_address:
            if odoo_address and so_address != odoo_address:
                raise UserError(
                    _(
                        "Delivery address ambiguity: there is one on the sale"
                        " and another on the partner. Please fill-in the"
                        " recipient partner field to desambiguify."
                    )
                )
            return so_address
        else:
            return odoo_address
