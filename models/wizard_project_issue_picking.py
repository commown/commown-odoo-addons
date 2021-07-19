from odoo import models, fields, api


class ProjectIssueAbstractPickingWizard(models.AbstractModel):
    _name = "project.issue.abstract.picking.wizard"

    issue_id = fields.Many2one(
        "project.issue",
        string=u"Issue",
        required=True,
    )

    date = fields.Datetime(
        string=u"date",
        required=True,
        default=lambda self: self._default_date(),
    )

    def _default_date(self):
        return fields.Datetime.now()

    @api.multi
    def _create_picking(self, orig_location, dest_location, lot):
        picking_type = self.env.ref("stock.picking_type_internal")
        contract = self.issue_id.contract_id

        picking_data = {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "min_date": self.date,
            "origin": contract.name,
            "move_lines": [
                (0, 0, {
                    "name": lot.product_id.name,
                    "picking_type_id": picking_type.id,
                    "location_id": orig_location.id,
                    "location_dest_id": dest_location.id,
                    "product_id": lot.product_id.id,
                    'product_uom_qty': lot.product_qty,
                    'product_uom': lot.product_uom_id.id,
                })
            ],
        }

        picking = self.env["stock.picking"].create(picking_data)
        picking.action_confirm()
        picking.action_assign()

        pack_op = picking.pack_operation_product_ids.ensure_one()
        pack_op.pack_lot_ids.unlink()
        pack_op.write({'pack_lot_ids': [(0, 0, {
            'lot_id': lot.id, 'lot_name': lot.name, 'qty': lot.product_qty,
        })]})
        pack_op.save()

        contract.picking_ids |= picking


class ProjectIssueOutwardPickingWizard(models.TransientModel):
    _name = "project.issue.outward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    location_id = fields.Many2one(
        "stock.location",
        string=u"Location",
        domain=lambda self: [(
            'location_id', '=', self.env.ref(
                'commown_devices.stock_location_available_for_rent').id)],
        required=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string=u"Product",
        domain="[('tracking', '=', 'serial')]",
        required=True,
        default=lambda self: self._default_product(),
    )

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        domain=("[('product_id', '=', product_id),"
                " ('location_id', '=', location_id)]"),
        required=True,
    )

    def _default_product(self):
        contract = self._issue().contract_id
        stockable = self.env["product.template"].search([
            ("contract_template_id", "=", contract.contract_template_id.id)
        ]).mapped("stockable_product_id")
        return stockable and stockable[0]

    def _issue(self):
        if "default_issue_id" in self.env.context:
            return self.env["project.issue"].browse(
                self.env.context["default_issue_id"])

    @api.multi
    def create_picking(self):
        self._create_picking(
            self.location_id,
            self.issue_id.partner_id.set_customer_location(),
            self.quant_id.lot_id
        )


class ProjectIssueInwardPickingWizard(models.TransientModel):
    _name = "project.issue.inward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        domain=lambda self: self._domain_quant(),
        required=True,
    )

    def _domain_quant(self):
        model = self.env.context.get("active_model")
        if model == "project.issue":
            issue = self.env[model].browse(self.env.context["active_id"])
            return [('location_id', '=',
                     issue.partner_id.property_stock_customer.id)]

    @api.multi
    def create_picking(self):
        self._create_picking(
            self.issue_id.partner_id.set_customer_location(),
            self.env.ref("commown_devices.stock_location_fp3_to_check"),
            self.quant_id.lot_id,
        )
