from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    default_product_grade = fields.Many2one(
        "commown_grade.grade",
        required=False,
        default=lambda self: self.env["commown_grade.grade"].search([], limit=1).id,
    )

    @api.multi
    def is_for_rental(self):
        "Return if current purchase picking type's destination is a rental location"
        self.ensure_one()
        loc = self.picking_type_id and self.picking_type_id.default_location_dest_id
        internal_rental_loc = self.env.ref("commown_devices.stock_location_rental")
        return loc and loc.parent_path.startswith(internal_rental_loc.parent_path)
