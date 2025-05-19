from odoo import api, models


class Message(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        """Circumvent an odoo bug

        The default_attachment_ids context key is ignored in standard odoo code,
        as the creation values are added an empty but existing attachment_ids
        key, which prevents the default_get method to pick the context's value.

        See https://github.com/odoo/odoo/blob/12.0/addons/mail/models/mail_message.py#L961
        """

        for values in vals_list:
            if (
                "attachment_ids" not in values
                and "default_attachment_ids" in self._context
            ):
                values["attachment_ids"] = self._context["default_attachment_ids"]
        return super().create(vals_list)
