from odoo import models, fields, api, _


class ProjectIssue(models.Model):
    _inherit = "project.issue"

    lot_id = fields.Many2one(
        string=u"Involved device",
        help=u"Device involved in present issue",
        comodel_name="stock.production.lot",
        default=lambda self: self._default_lot_id(),
        domain=lambda self: self._domain_lot_id(),
    )

    def _default_lot_id(self):
        domain = self._domain_lot_id()
        if domain:
            if self.env["stock.production.lot"].search_count(domain) == 1:
                return self.env["stock.production.lot"].search(domain)

    def _domain_lot_id(self):
        domain = []
        if self.contract_id:
            domain.append(
                ("id", "in", self.contract_id.mapped("quant_ids.lot_id").ids))
        return domain

    @api.onchange("contract_id")
    def onchange_contract_id_set_lot_id(self):
        # Protect against onchange loop
        if self.lot_id not in self.contract_id.mapped("quant_ids.lot_id"):
            self.lot_id = self._default_lot_id() or False
        return {"domain": {"lot_id": self._domain_lot_id()}}

    @api.onchange("lot_id")
    def onchange_lot_id_set_contract(self):
        if self.lot_id and not self.contract_id:
            contracts = self.lot_id.mapped("quant_ids.contract_id")
            if len(contracts) == 1:
                self.contract_id = contracts.id

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
