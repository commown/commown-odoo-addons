import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _inherit = "res.users"

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        "Disable automatic email sending when creating users"
        if self._context.get("import_file", False):
            _logger.info("Reset password is disabled while importing users")
            self = self.with_context(no_reset_password=True)
        return super(res_users, self).create(vals)
