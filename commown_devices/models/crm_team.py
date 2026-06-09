from odoo import models


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = [
        "crm.team",
        "commown_devices.picking_order_parent_mixin",
    ]
