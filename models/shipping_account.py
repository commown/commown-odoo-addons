from odoo import models, fields


class CommownShippingAccount(models.Model):
    _name = 'commown.shipping_account'
    _description = 'Shipping account data'
    _inherit = ["server.env.mixin"]

    name = fields.Char(required=True)
    account = fields.Char(string='Account Number', required=True)
    password = fields.Char(string='Account Password', required=True)

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        shipping_fields = {
            "account": {},
            "password": {},
        }
        shipping_fields.update(base_fields)
        return shipping_fields
