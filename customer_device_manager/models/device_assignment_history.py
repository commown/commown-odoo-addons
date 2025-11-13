from odoo import fields, models


class DeviceAssignmentHistory(models.Model):
    _name = "customer_device_manager.device_assignment_history"
    _description = "Store the partner an assignment had at one given date"

    _order = "assignment_id, date desc, id desc"

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
        domain="[('type', 'in', ['contact', 'other'])]",
    )

    device_location = fields.Selection(
        [
            ("at_customer", "At Customer"),
            ("at_commown", "At Commown"),
        ],
        string="Device Location",
        required=True,
        default="at_customer",
    )

    def name_get(self):
        result = []
        for rec in self:
            rec_date = fields.Datetime.to_string(rec.date)
            name = (
                f"{rec.assignment_id.device_name} - {rec.partner_id.name}"
                f" ({rec_date})"
            )
            result.append((rec.id, name))
        return result
