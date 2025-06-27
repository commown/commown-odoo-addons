from odoo import api, fields, models


class UrbanMinePartner(models.Model):
    _inherit = "res.partner"

    from_urban_mine = fields.Boolean("From urban mine registration")

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)

        for partner in partners:
            if partner.from_urban_mine:
                task = self.env["project.task"].create(
                    {
                        "name": partner.name + " - " + partner.city,
                        "partner_id": partner.id,
                        "project_id": self.env.ref("urban_mine.project").id,
                        "stage_id": self.env.ref("urban_mine.stage1").id,
                    }
                )

                task.name = task.urban_mine_name() + " " + task.name

        return partners
