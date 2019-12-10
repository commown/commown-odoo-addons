from odoo import models, api, fields, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    contractual_issue_ids = fields.One2many(
        comodel_name='project.task',
        inverse_name='contract_id',
        string='Contractual issues')

    other_issue_ids = fields.One2many(
        comodel_name='project.issue',
        inverse_name='contract_id',
        string='Other issues')
