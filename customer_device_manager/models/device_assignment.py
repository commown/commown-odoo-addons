from odoo import fields, models


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
    )

    assignment_notes = fields.Text(
        string="Notes",
    )

    active = fields.Boolean("Active", default=True)

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
                }
            )

    def name_get(self):
        return [(rec.id, rec.device_id.name) for rec in self]
