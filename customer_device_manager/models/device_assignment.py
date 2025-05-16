from odoo import api, fields, models


class DeviceAssignment(models.Model):
    """
    This model represents the assignment of a device to a partner. The partner assigned
    to a device can change over time, but the history of these changes is preserved
    in the DeviceAssignmentHistory model via the _inverse_partner_id method.

    Each time the partner_id field is changed, a new history record is automatically
    created.
    """

    _name = "customer_device_manager.device_assignment"
    _description = "Device Assignment"
    _order = "assignment_date desc, id desc"
    _rec_name = "device_name"

    device_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="User",
        required=True,
        inverse="_inverse_partner_id",
    )

    assignment_date = fields.Datetime(
        string="Assignment Date",
        required=True,
        default=fields.Datetime.now,
        compute="_compute_history_change_impact",
        store=True,
        readonly=True,
    )

    assignment_notes = fields.Text(
        string="Notes",
    )

    device_location = fields.Selection(
        [
            ("at_customer", "At Customer"),
            ("at_commown", "At Commown"),
        ],
        string="Device Location",
        default="at_customer",
        compute="_compute_history_change_impact",
        store=True,
        readonly=True,
    )

    history_ids = fields.One2many(
        "customer_device_manager.device_assignment_history",
        inverse_name="assignment_id",
    )

    image_medium = fields.Binary(
        string="Product Image",
        related="device_id.product_id.image_medium",
        store=False,
    )

    device_name = fields.Char(
        string="Serial Number / IMEI",
        related="device_id.name",
        store=False,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        related="device_id.product_id",
        store=False,
        readonly=True,
    )

    contract_name = fields.Char(
        string="Contract",
        related="device_id.contract_id.name",
        store=False,
        readonly=True,
    )

    def _inverse_partner_id(self):
        for rec in self:
            self.env["customer_device_manager.device_assignment_history"].sudo().create(
                {
                    "assignment_id": rec.id,
                    "date": fields.Datetime.now(),
                    "partner_id": rec.partner_id.id,
                    "device_location": rec.device_location,
                }
            )

    @api.depends("history_ids.date")
    def _compute_history_change_impact(self):
        for rec in self:
            last_history = rec.history_ids and rec.history_ids[0]
            if last_history:
                rec.update(
                    {
                        "device_location": last_history.device_location,
                        "assignment_date": last_history.date,
                    }
                )
            else:
                rec.update(
                    {
                        "device_location": "at_customer",
                        "assignment_date": fields.Datetime.now(),
                    }
                )

    def name_get(self):
        return [(rec.id, rec.device_id.name) for rec in self]
