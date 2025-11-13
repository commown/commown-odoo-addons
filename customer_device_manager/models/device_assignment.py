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
        "stock.lot",
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
        domain="[('type', 'in', ['contact', 'other'])]",
    )

    assignment_date = fields.Datetime(
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
        default="at_customer",
        compute="_compute_history_change_impact",
        store=True,
        readonly=True,
    )

    history_ids = fields.One2many(
        "customer_device_manager.device_assignment_history",
        inverse_name="assignment_id",
    )

    image_128 = fields.Image(
        string="Product Image",
        related="device_id.product_id.image_128",
        store=False,
    )

    device_name = fields.Char(
        string="Serial Number / IMEI",
        related="device_id.name",
        store=False,
    )

    product_name = fields.Char(
        string="Product",
        related="device_id.product_id.name",
        store=True,
        readonly=True,
    )

    contract_name = fields.Char(
        string="Contract",
        compute="_compute_contract_name",
        store=True,
        readonly=True,
    )

    @api.model
    def create(self, values):
        "Force first assignment history item date to the one of the assignment"
        _self, orig_context = self, self._context

        _date = values.get("assignment_date")
        if _date:
            _self = self.with_context(forced_assignment_history_date=_date)

        # Restore the original context in the returned result to avoid any side effect:
        return super(DeviceAssignment, _self).create(values).with_context(orig_context)  # pylint: disable=context-overridden

    def _inverse_partner_id(self):
        for rec in self:
            _date = self.env.context.get(
                "forced_assignment_history_date",
                fields.Datetime.now(),
            )
            self.env["customer_device_manager.device_assignment_history"].sudo().create(
                {
                    "assignment_id": rec.id,
                    "date": _date,
                    "partner_id": rec.partner_id.id,
                    "device_location": rec.device_location,
                }
            )

    @api.depends("history_ids.date")
    def _compute_history_change_impact(self):
        for rec in self:
            rec.invalidate_recordset(["history_ids"])
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

    @api.depends("device_id.contract_id")
    def _compute_contract_name(self):
        for record in self:
            commercial_partner = record.partner_id.commercial_partner_id
            sudo_contract = record.device_id.sudo().contract_id
            if sudo_contract.commercial_partner_id == commercial_partner:
                record.contract_name = sudo_contract.name
            else:
                record.contract_name = False

    def name_get(self):
        return [(rec.id, rec.device_id.name) for rec in self]

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        hide_fields_in_filters = (
            "create_date",
            "create_uid",
            "write_date",
            "write_uid",
            "history_ids",
            "device_id",
        )
        for fname in result.keys() & hide_fields_in_filters:
            result[fname]["searchable"] = False
        return result
