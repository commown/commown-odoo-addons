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
    groups = fields.Many2many(
        "res.groups",
        string="Corresponding groups",
    )
