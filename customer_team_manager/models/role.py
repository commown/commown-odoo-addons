from odoo import fields, models


class CustomerEmployeeRole(models.Model):
    "Represents the relationship between a customer role and res.users.role"

    _name = "customer_team_manager.employee.role"
    _description = "Role of the employee of a customer has in its organization"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Employee role already exists!"),
    ]

    name = fields.Char(
        required=True,
        translate=True,
    )
    description = fields.Char(
        translate=True,
    )
    color = fields.Char(
        string="Color",
    )
    icon_name = fields.Char(
        string="Icon name (fontawesome)",
        help="Example: 'fa-lock'",
    )
    nodelete = fields.Boolean(
        compute="_compute_nodelete",
        store=False,
    )
    groups = fields.Many2many(
        "res.groups",
        string="Corresponding groups",
        domain=lambda self: [("category_id.name", "=", "Manager customer")],
    )

    def _compute_nodelete(self):
        employee_role = self.env.ref("customer_team_manager.customer_role_user")
        for rec in self:
            rec.nodelete = bool(rec.id == employee_role.id)
