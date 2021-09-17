from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):

    env = Environment(cr, SUPERUSER_ID, {})
    env['project.project'].search([
        ('contractual_issues_tracking', '=', True)
    ]).update({'require_contract': True})
