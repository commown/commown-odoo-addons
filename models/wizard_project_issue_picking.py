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
        help=u"Defaults to now - To be set only to force a date",
    )



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
        self.issue_id.contract_id.send_device(
            self.quant_id.lot_id, self.location_id, date=self.date)


class ProjectIssueInwardPickingWizard(models.TransientModel):
    _name = "project.issue.inward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        domain=lambda self: self._domain_quant(),
        required=True,
    )

    location_dest_id = fields.Many2one(
        "stock.location",
        string=u"Destination",
        domain=lambda self: [(
            'location_id', '=', self.env.ref(
                'commown_devices.stock_location_devices_to_check').id)],
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
        self.issue_id.contract_id.receive_device(
            self.quant_id.lot_id, self.location_dest_id, date=self.date)
