from odoo import models, api


class CommownProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'commown.shipping.mixin']

    _shipping_parent_rel = 'project_id'
