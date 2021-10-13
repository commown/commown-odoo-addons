from odoo import fields, models


class KeychainAccount(models.Model):
    _inherit = 'keychain.account'

    namespace = fields.Selection(
        selection_add=[('telecommown', 'TeleCommown')])

    def _telecommown_init_data(self):
        return {}

    def _telecommown_validate_data(self, data):
        return True
