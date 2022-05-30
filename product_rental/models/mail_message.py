from odoo import api, models


class Message(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        if not 'attachment_ids' in values and 'default_attachment_ids' in self._context:
            values['attachment_ids'] = self._context['default_attachment_ids']
        return super().create(values)
