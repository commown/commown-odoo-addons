from odoo import models, api, fields, _


class Contract(models.Model):
    _inherit = 'contract.contract'

    issue_ids = fields.One2many(
        comodel_name='project.task',
        inverse_name='contract_id',
        string='Related tasks')
