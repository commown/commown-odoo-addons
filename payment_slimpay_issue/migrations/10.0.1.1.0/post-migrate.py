import re

from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):

    LABEL_RE = re.compile('^Payment Label: (.*)', flags=re.MULTILINE)

    env = Environment(cr, SUPERUSER_ID, {})
    project = env.ref('payment_slimpay_issue.project_payment_issue')
    issues = env['project.issue'].search([('project_id', '=', project.id)])

    for issue in issues:
        match = LABEL_RE.search(issue.description)
        if match:
            issue.slimpay_payment_label = match.group(1)
