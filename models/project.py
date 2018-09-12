from odoo import models, fields


class Project(models.Model):
    _inherit = 'project.project'

    contractual_issues_tracking = fields.Boolean(
        'Contractual_issues_tracking', default=False)
