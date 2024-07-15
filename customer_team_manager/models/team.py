from odoo import api, fields, models


class Team(models.Model):
    _name = "customer_team_manager.team"
    _inherit = "customer_team_manager.customer_company_object"
    _description = "A team of a customer"

    _rec_name = "full_name"
    _order = "company, full_name"

    name = fields.Char(
        required=True,
        index=True,
    )

    full_name = fields.Char(
        string="Full Name",
        compute="_compute_full_name",
        store=True,
    )

    parent_team = fields.Many2one(
        "customer_team_manager.team",
        index=True,
    )

    @api.onchange("company")
    def _onchange_company_set_parent_team_domain(self):
        if self.env.user.has_group("sales_team.group_sale_manager"):
            return {
                "domain": {
                    "parent_team": [("company", "=", self.company.id)],
                }
            }

    @api.depends("name", "parent_team.full_name")
    def _compute_full_name(self):
        for team in self:
            if team.parent_team:
                team.full_name = "%s / %s" % (team.parent_team.full_name, team.name)
            else:
                team.full_name = team.name
