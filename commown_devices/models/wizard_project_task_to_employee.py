from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProjectTaskDeviceToEmployeeWizard(models.TransientModel):
    _name = "project.task.to.employee.wizard"
    _description = "Wizard to give a device to an employee"

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        domain=lambda self: self._domain_lot_id(),
        required=True,
    )

    date = fields.Datetime(
        string="Date",
        help="Defaults to now - To be set only to force a date",
    )

    delivered_by_hand = fields.Boolean(
        "Delivered by hand?",
        help="Unset if the device must be sent by post",
        default=True,
    )

    def _domain_lot_id(self):
        loc_avail = self.env.ref("commown_devices.stock_location_available_for_rent")
        quant_domain = [("location_id", "child_of", loc_avail.id)]
        quants = (
            self.env["stock.quant"]
            .search(quant_domain)
            .filtered(lambda q: q.quantity > q.reserved_quantity)
        )
        return [("id", "in", quants.mapped("lot_id").ids)]

    @api.multi
    def execute(self):
        self.ensure_one()

        # Consistency checks:

        # - Partner must be an employee
        if not self.task_id.partner_id:
            raise UserError(_("Please set the task's partner before using this wizard"))

        if self.task_id.partner_id.commercial_partner_id.id != 1:
            raise UserError(_("Please use an employee as a partner"))

        # - Device must be available for rent
        loc_avail = self.env.ref("commown_devices.stock_location_available_for_rent")
        quant_domain = [
            ("location_id", "child_of", loc_avail.id),
            ("lot_id", "=", self.lot_id.id),
        ]
        quants = (
            self.env["stock.quant"]
            .search(quant_domain)
            .filtered(lambda q: q.quantity > q.reserved_quantity)
        )
        if len(quants) != 1:
            raise UserError(_("Cannot find given device. Is it really available?"))

        # Create the contract and send the device:

        ct = self.env.ref("commown_devices.contract_template_to_employee")
        partner = self.task_id.partner_id
        pt = self.lot_id.product_id.product_tmpl_id
        cname = _("%(product)s for %(partner)s")
        contract = self.env["contract.contract"].create(
            {
                "name": cname % {"product": pt.name, "partner": partner.name},
                "contract_template_id": ct.id,
                "partner_id": partner.id,
            }
        )
        contract._onchange_contract_template_id()

        # Waiting for the effective delivery before starting the contract is not
        # important here, so its simpler to do it at the given date:
        dtime = self.date or fields.Datetime.now()
        contract.date_start = dtime.date()
        contract.send_devices(
            self.lot_id,
            {},
            {},
            date=dtime,
            do_transfer=self.delivered_by_hand,
        )

        self.task_id.update(
            {
                "lot_id": self.lot_id.id,
                "storable_product_id": self.lot_id.product_id.id,
                "contract_id": contract.id,
            }
        )

        return contract
