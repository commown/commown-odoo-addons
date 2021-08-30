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


class ProjectIssueContractTransferWizard(models.Model):
    _name = "project.issue.contract_transfer.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    contract_id = fields.Many2one(
        "account.analytic.account",
        string=u"Destination contract",
        required=True,
        domain=[("recurring_invoices", "=", True), ("date_end", "=", False)],
    )

    @api.multi
    def create_transfer(self):
        lot = self.issue_id.lot_id
        if not lot:
            raise UserError(_("Can't move device: no device set on this issue!"))

        transfer_location = self.env.ref(
            "commown_devices.stock_location_contract_transfer")

        self.issue_id.contract_id.receive_device(
            self.issue_id.lot_id, transfer_location, date=self.date,
            do_transfer=True)

        dest = self.contract_id.partner_id.set_customer_location()

        self.contract_id.send_device(
            self.issue_id.lot_id.quant_ids[0], date=self.date, do_transfer=True)



class ProjectIssueOutwardPickingWizard(models.TransientModel):
    _name = "project.issue.outward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    product_id = fields.Many2one(
        "product.product",
        string=u"Product",
        domain="[('tracking', '=', 'serial')]",
        required=True,
        default=lambda self: self._compute_default_product_id(),
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        string=u"Device",
        domain=lambda self: '''[
            ("product_id", "=", product_id),
            ("quant_ids.location_id", "child_of", %d)]''' % self.env.ref(
                "commown_devices.stock_location_available_for_rent").id,
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
            self.lot_id.quant_ids[0], date=self.date)


class ProjectIssueInwardPickingWizard(models.TransientModel):
    _name = "project.issue.inward.picking.wizard"
    _inherit = "project.issue.abstract.picking.wizard"

    quant_id = fields.Many2one(
        "stock.quant",
        string=u"Device",
        required=True,
    )

    location_dest_id = fields.Many2one(
        "stock.location",
        string=u"Destination",
        domain=lambda self: [(
            'id', '=', self.env.ref(
                'commown_devices.stock_location_devices_to_check').id)],
        required=True,
    )

    @api.onchange("issue_id")
    def onchange_issue_id(self):
        if self.issue_id:
            quants = self.issue_id.contract_id.quant_ids
            return {
                "domain": {
                    "quant_id": [("id", "in", quants.ids)]
                }
            }

    @api.multi
    def create_picking(self):
        return self.issue_id.contract_id.receive_device(
            self.quant_id.lot_id, self.location_dest_id, date=self.date)
