from odoo import models, fields


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = [
        "crm.team",
        "commown.delivery.parent.mixin",
    ]
