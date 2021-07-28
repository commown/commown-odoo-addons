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
