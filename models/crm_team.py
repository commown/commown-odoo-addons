from odoo import models


class CrmTeam(models.Model):
    _name = 'crm.team'
    _inherit = ['crm.team', 'commown.shipping.parent.mixin']
