from odoo import api, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "commown.shipping.mixin"]

    _shipping_parent_rel = "project_id"

    @api.multi
    def get_label_ref(self):
        self.ensure_one()
        return "SAV%d" % self.id
