import logging

from odoo import models, api, fields, _


_logger = logging.getLogger(__name__)


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    contract_id = fields.Many2one(
        'account.analytic.account', string='Contract')
