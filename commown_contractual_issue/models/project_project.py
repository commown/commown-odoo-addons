from odoo import models, fields, api


class Project(models.Model):
    _inherit = 'project.project'

    require_contract = fields.Boolean(
        'Tasks require a contract', default=False)
    contractual_issues_tracking = fields.Boolean(
        'Contractual_issues_tracking', default=False)

    @api.constrains('require_contract', 'contractual_issues_tracking')
    def _check_contract_coherency(self):
        for r in self:
            if r.contractual_issues_tracking and not r.require_contract:
                raise models.ValidationError(
                    'A contract must be set on tasks to track '
                    'contractual issues')
