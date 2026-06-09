from odoo import fields, models


class PickingOrderParentMixin(models.AbstractModel):
    _name = "commown_devices.picking_order_parent_mixin"
    _description = "Class holding the fields and methods to create pickings"

    carrier_account_id = fields.Many2one(
        "carrier.account",
        string="Carrier account",
    )

    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Picking type",
    )

    picking_scheduled_in_days = fields.Integer(
        string="Scheduled in how many days?",
        default=0,
        required=True,
    )

    picking_scheduled_forced_hour = fields.Integer(
        string="Scheduled hour?", help="-1 to use current time", default=-1
    )

    picking_os_required = fields.Boolean(
        string="OS indication required",
    )

    picking_orig = fields.Many2one(
        "stock.location",
        string="Origin location",
    )

    picking_dest_contract_partner = fields.Boolean(
        string="Use contract-specific destination?",
    )

    picking_dest = fields.Many2one(
        "stock.location",
        string="Destination location",
    )

    picking_return_to = fields.Many2one(
        "stock.location",
        string="Return location",
        help="If returns are possible, specify their destination here",
    )
