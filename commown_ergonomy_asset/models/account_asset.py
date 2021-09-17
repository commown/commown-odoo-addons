from odoo import api, fields, models, _


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    _name = 'account.asset.asset'

    value_residual = fields.Float(store=True)
