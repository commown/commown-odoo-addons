from odoo import api, fields, models


class UrbanMinePartner(models.Model):
    _inherit = "res.partner"

    from_urban_mine = fields.Boolean(
        "From urban mine registration", website_form_blacklisted=False
    )

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        result = super().create(vals)

        if vals.get("from_urban_mine", False):

            task = self.env["project.task"].create(
                {
                    "name": result.name + " - " + result.city,
                    "partner_id": result.id,
                    "project_id": self.env.ref("urban_mine.project").id,
                    "stage_id": self.env.ref("urban_mine.stage1").id,
                }
            )

            task.name = ("[COMMOWN-MU-%d] " % task.id) + task.name

        return result
