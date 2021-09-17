from odoo import models, fields, api, _


class ProjectIssue(models.Model):
    _inherit = "project.issue"

    lot_id = fields.Many2one(
        string=u"Involved device",
        help=u"Device involved in present issue",
        comodel_name="stock.production.lot",
        default=lambda self: self._default_lot_id(),
    )

    @api.onchange("contract_id")
    def onchange_contract_id(self):
        result = {}
        if self.contract_id:
            lots = self.contract_id.stock_at_date()
            result["domain"] = {"lot_id": [('id', 'in', lots.ids)]}
        return result

    def _contract(self):
        if not self.contract_id and "contract_id" in self.env.context:
            return self.env["account.analytic.account"].browse(
                self.env.context["contract_id"])
        else:
            return self.contract_id

    def _default_lot_id(self):
        "Returns the first lot_id found from contract quant_ids at present date"
        contract = self._contract()
        if contract:
            date = self.create_date or fields.Datetime.now()
            stock = contract.stock_at_date(date)
        else:
            stock = self.env["stock.production.lot"]
        return stock and stock[0]

    def action_scrap_device(self):
        scrap_loc = self.env.ref("stock.stock_location_scrapped")

        ctx = {
            "default_product_id": self.lot_id.product_id.id,
            "default_lot_id": self.lot_id.id,
            "default_origin": self.contract_id.name,
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
