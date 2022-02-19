from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    storable_product_id = fields.Many2one(
        string="Article",
        comodel_name="product.product",
        domain=lambda self: self._compute_storable_product_domain(),
    )

    lot_id = fields.Many2one(
        string="Device",
        comodel_name="stock.production.lot",
        domain=lambda self: self._compute_lot_domain(),
    )

    device_tracking = fields.Boolean(
        'Use for device tracking?',
        related='project_id.device_tracking')

    def _compute_storable_product_domain(self):
        if not self.contract_id:
            domain = [('tracking', '=', 'serial')]
        else:
            lots = self.contract_id.quant_ids.mapped("lot_id")
            products = lots.mapped("product_id")
            domain = [("id", "in", products.ids)]
        return domain

    def _compute_lot_domain(self):
        product = self.storable_product_id

        if self.contract_id:
            quants = self.contract_id.quant_ids

        elif self.partner_id:
            quants = self.env["contract.contract"].search([
                ("partner_id.commercial_partner_id", "=",
                 self.partner_id.commercial_partner_id.id),
            ]).mapped('quant_ids')
            if product:
                quants = quants.filtered(
                    lambda q: q.lot_id.product_id == product.id)

        else:
            qdom = [("quantity", ">", 0),
                    "|",
                    ("location_id", "child_of", self.env.ref(
                        "commown_devices.stock_location_devices_to_check").id),
                    ("location_id", "child_of", self.env.ref(
                        "commown_devices.stock_location_new_devices").id),
                    ]
            if product:  # optimize the request a bit
                qdom.append(("lot_id.product_id", "=", product.id))
            quants = self.env["stock.quant"].search(qdom)

        domain = [("id", "in", quants.mapped("lot_id").ids)]

        if product:
            domain.append(("product_id", "=", product.id))

        return domain

    def _reset_field_target(self, field_name, domain):
        value = getattr(self, field_name)
        model = self.env[self._fields[field_name].comodel_name]
        possible_values = model.search(domain)
        if len(possible_values) == 1:
            setattr(self, field_name, possible_values)
        elif value and value not in possible_values:
            setattr(self, field_name, False)

    @api.onchange("partner_id")
    def onchange_partner_id_set_lot_id(self):
        "if contract_id could not be guessed, restrict lot_id at best"
        if not self.contract_id:  # otherwise another onchange will do the job
            lot_domain = self._compute_lot_domain()
            self._reset_field_target("lot_id", lot_domain)
            return {"domain": {"lot_id": lot_domain}}

    @api.onchange("contract_id", "storable_product_id")
    def onchange_contract_or_product(self):
        lot_domain = self._compute_lot_domain()
        product_domain = self._compute_storable_product_domain()

        self._reset_field_target("lot_id", lot_domain)
        self._reset_field_target("storable_product_id", product_domain)

        return {
            "domain": {
                "lot_id": lot_domain,
                "storable_product_id": product_domain,
            }
        }

    @api.onchange("lot_id")
    def onchange_lot_id(self):
        if self.lot_id:
            self.storable_product_id = self.lot_id.product_id
            if not self.contract_id:
                contracts = self.lot_id.mapped("quant_ids").filtered(
                    lambda q: q.quantity > 0).mapped("contract_id")
                if len(contracts) == 1:
                    self.contract_id = contracts.id

    def action_scrap_device(self):
        scrap_loc = self.env.ref("stock.stock_location_scrapped")

        ctx = {
            "default_product_id": self.lot_id.product_id.id,
            "default_lot_id": self.lot_id.id,
            "default_origin": "Task-%s" % self.id,
            "default_scrap_location_id": scrap_loc.id,
            }

        current_loc = self.env['stock.quant'].search([
            ('lot_id', '=', self.lot_id.id),
            ('quantity', '>', 0),
        ]).location_id
        if current_loc:
            ctx["default_location_id"] = current_loc[0].id

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.scrap",
            "name": _("Scrap device"),
            "view_mode": "form",
            "view_type": "form",
            "context": ctx,
        }
