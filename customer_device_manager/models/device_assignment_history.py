from odoo import api, fields, models


class DeviceAssignmentHistory(models.Model):
    _name = "customer_device_manager.device_assignment_history"
    _description = "Store the partner an assignment had at one given date"

    _order = "assignment_id, date desc"

    assignment_id = fields.Many2one(
        "customer_device_manager.device_assignment",
        string="Serial Number / IMEI",
        index=True,
        required=True,
    )

    date = fields.Datetime(default=fields.Datetime.now, required=True)

    partner_id = fields.Many2one(
        "res.partner",
        string="User",
        index=True,
        required=True,
    )

    is_current_assignment = fields.Boolean(
        string="Current Assignments",
        compute="_compute_is_current_assignment",
        store=True,
    )

    device_status = fields.Selection(
        [
            ("in_house", "In House"),
            ("returned", "Returned"),
        ],
        string="Device Status",
        compute="_compute_device_status",
        store=True,
        help="Indicates if the device is currently in house or has been returned.",
    )

    @api.depends("assignment_id.partner_id", "partner_id", "assignment_id.active")
    def _compute_is_current_assignment(self):
        for record in self:
            record.is_current_assignment = (
                record.partner_id == record.assignment_id.partner_id
                and record.assignment_id.active
            )

    @api.depends("assignment_id.active")
    def _compute_device_status(self):
        for record in self:
            if record.assignment_id.active:
                record.device_status = "in_house"
            else:
                record.device_status = "returned"

    def name_get(self):
        return [
            (r.id, r.assignment_id.device_name or str(r.assignment_id.id)) for r in self
        ]
