import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class CommownResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        "Disable automatic email sending when creating users"
        if self._context.get("import_file", False):
            _logger.info("Reset password is disabled while importing users")
            self = self.with_context(no_reset_password=True)
        return super().create(vals_list)
