import logging

from odoo import models, api, fields, _


_logger = logging.getLogger(__name__)


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    contract_id = fields.Many2one(
        'account.analytic.account', string='Contract')
    commercial_partner_id = fields.Many2one(
        'res.partner', related='partner_id.commercial_partner_id')
