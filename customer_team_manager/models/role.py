from odoo import fields, models


class CustomerRole(models.Model):
    "Represents the relationship between a customer partner and res.groups"

    _name = "customer_team_manager.customer_role"
    _description = "Role of the customer in its organization"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Customer role already exists!"),
    ]
    _order = "sequence, id"

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

    sequence = fields.Integer()

    groups = fields.Many2many(
        "res.groups",
        string="Corresponding groups",
        readonly=True,  # Would not user group sync, not yet available
        domain=lambda self: [("category_id.name", "=", "Manager customer")],
    )
