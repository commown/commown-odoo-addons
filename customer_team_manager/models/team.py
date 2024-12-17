from odoo import api, fields, models


class Team(models.Model):
    _name = "customer_team_manager.team"
    _description = "A team of a customer"

    _rec_name = "full_name"
    _order = "customer_company, full_name"

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

    customer_company = fields.Many2one(
        "res.partner",
        string="Company",
        groups="sales_team.group_sale_manager",
        default=lambda self: self._default_customer_company(),
        domain=[("is_company", "=", True)],
        required=True,
        index=True,
        copy=False,
    )

    def _default_customer_company(self):
        if self.env.user.has_group("customer_team_manager.group_customer_admin"):
            return self.env.user.commercial_partner_id.id

    @api.onchange("customer_company")
    def _onchange_customer_company_set_parent_team_domain(self):
        if self.env.user.has_group("sales_team.group_sale_manager"):
            comp_id = self.customer_company.id
            return {
                "domain": {
                    "parent_team": [("customer_company", "=", comp_id)],
                }
            }

    @api.depends("name", "parent_team.full_name")
    def _compute_full_name(self):
        for team in self:
            if team.parent_team:
                team.full_name = "%s / %s" % (team.parent_team.full_name, team.name)
            else:
                team.full_name = team.name
