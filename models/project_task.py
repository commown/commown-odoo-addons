from odoo import models, api, fields, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    contract_id = fields.Many2one(
        'account.analytic.account', string='Contract')
    commercial_partner_id = fields.Many2one(
        'res.partner', related='partner_id.commercial_partner_id')
    contractual_issue_type = fields.Selection(
        [('loss', 'Loss'), ('breakage', 'Breakage'), ('theft', 'Theft')],
        string='Issue type',
    )
    contractual_issue_date = fields.Date(
        'Issue date',
        help='Date when the contractual issue occurred')
    penalty_exemption = fields.Boolean(
        'Penalty exemption', help='E.g.: customer paid, commercial initiative',
        default=False)
    contractual_issues_tracking = fields.Boolean(
        'Used for contractual issue tracking',
        related='project_id.contractual_issues_tracking')
