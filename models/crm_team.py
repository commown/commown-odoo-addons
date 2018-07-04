from odoo import models, fields


class CommownCrmTeam(models.Model):
    _inherit = 'crm.team'

    custom_lead_view_id = fields.Many2one(
        'ir.ui.view', string='Custom lead view',
        domain="[('model', '=', 'crm.lead')]")
