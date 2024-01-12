from odoo import fields, models


class CustomerCompanyObject(models.AbstractModel):

    _name = "customer_team_manager.customer_company_object"
    _description = "A customer abstract object related to its company"

    company = fields.Many2one(
        "res.partner",
        string="Company",
        groups="customer_team_manager.group_manager",
        default=lambda self: self._default_company(),
        domain=[("is_company", "=", True)],
        required=True,
        index=True,
        copy=False,
    )

    def _default_company(self):
        if self.env.user.has_group("customer_team_manager.group_customer_admin"):
            return self.env.user.commercial_partner_id.id
