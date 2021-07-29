from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    storable_product_id = fields.Many2one(
        string=u"Article",
        comodel_name="product.product",
        domain="[('tracking', '=', 'serial')]",
    )

    lot_id = fields.Many2one(
        string=u"Device",
        comodel_name="stock.production.lot",
    )

    device_tracking = fields.Boolean(
        'Use for device tracking?',
        related='project_id.device_tracking')

    @api.onchange("storable_product_id")
    def onchange_storable_product(self):
        result = {}
        if self.storable_product_id:
            loc_check = self.env.ref(
                "commown_devices.stock_location_devices_to_check")
            domain = [("location_id", "child_of", loc_check.id)]
            if self.storable_product_id:
                domain.append(("product_id", "=", self.storable_product_id.id))
            lots = self.env["stock.quant"].search(domain).mapped("lot_id")
            result["domain"] = {"lot_id": [('id', 'in', lots.ids)]}
        return result

    def action_scrap_device(self):
        scrap_loc = self.env.ref("stock.stock_location_scrapped")

        ctx = {
            "default_product_id": self.lot_id.product_id.id,
            "default_lot_id": self.lot_id.id,
            "default_origin": self.name,
            "default_scrap_location_id": scrap_loc.id,
            }

        current_loc = self.env['stock.quant'].search([
            ('lot_id', '=', self.lot_id.id),
        ]).location_id
        if current_loc:
            ctx["default_location_id"] = current_loc[0].id

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.scrap",
            "name": _("Scrap device"),
            "view_mode": u"form",
            "view_type": u"form",
            "context": ctx,
        }
