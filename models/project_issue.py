from odoo import api, models


class CommownProjectIssue(models.Model):
    _name = "project.issue"
    _inherit = ["project.issue", "commown.shipping.mixin"]

    _shipping_parent_rel = "project_id"

    @api.multi
    def get_label_ref(self):
        self.ensure_one()
        return "SAV%d" % self.id
