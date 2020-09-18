from odoo import models, api


class CommownProjectIssue(models.Model):
    _name = 'project.issue'
    _inherit = ['project.issue', 'commown.shipping.mixin']

    _shipping_parent_rel = 'project_id'
