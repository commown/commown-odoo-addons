from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):

    env = Environment(cr, SUPERUSER_ID, {})
    issues = env['project.issue'].search([()])
    issues._compute_last_partner_msg_date()
