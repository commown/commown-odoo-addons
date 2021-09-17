from odoo import fields, models


class KeychainAccount(models.Model):
    _inherit = 'keychain.account'

    namespace = fields.Selection(
        selection_add=[('colissimo', 'Colissimo')])

    def _colissimo_init_data(self):
        return {}

    def _colissimo_validate_data(self, data):
        return True
