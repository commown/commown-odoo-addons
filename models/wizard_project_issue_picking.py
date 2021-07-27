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
        default=lambda self: self._compute_default_product_id(),
    )

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        domain=("[('product_id', '=', product_id),"
                " ('location_id', '=', location_id)]"),
        required=True,
    )

    def _compute_default_product_id(self):
        if not self.issue_id and "default_issue_id" in self.env.context:
            issue = self.env["project.issue"].browse(
                self.env.context["default_issue_id"])
        else:
            issue = self.issue
        return issue.lot_id.product_id

    @api.multi
    def create_picking(self):
        return self.issue_id.contract_id.send_device(
            self.quant_id, date=self.date)


class ProjectIssueInwardPickingWizard(models.TransientModel):
    _name = "project.issue.inward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        domain="[('id', 'in', contract_quant_ids)]",
        required=True,
    )

    contract_quant_ids = fields.One2many(
        "stock.quant",
        related=("issue_id.contract_id.quant_ids"),
    )

    location_dest_id = fields.Many2one(
        "stock.location",
        string=u"Destination",
        domain=lambda self: [(
            'location_id', '=', self.env.ref(
                'commown_devices.stock_location_devices_to_check').id)],
        required=True,
    )

    @api.multi
    def create_picking(self):
        return self.issue_id.contract_id.receive_device(
            self.quant_id.lot_id, self.location_dest_id, date=self.date)
