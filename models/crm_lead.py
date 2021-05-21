from odoo import models, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"

    contract_id = fields.Many2one(
        'account.analytic.account',
        string=u'Contract')
