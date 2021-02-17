from odoo import fields, models


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ["crm.team", "commown.shipping.parent.mixin"]

    used_for_shipping = fields.Boolean("Used for shipping", default=False)
    default_perform_actions_on_delivery = fields.Boolean(
        "By default, perform actions on delivery", default=True
    )
    on_delivery_email_template_id = fields.Many2one(
        "mail.template", string="Default delivery email model for this team"
    )
