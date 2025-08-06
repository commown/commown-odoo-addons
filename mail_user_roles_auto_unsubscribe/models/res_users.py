from odoo import api, models


class res_users(models.Model):
    _inherit = "res.users"

    def _filter_private_channel_removed_group(self, channel):
        removed_roles = self._origin.role_ids.filtered(lambda r: r not in self.role_ids)
        removed_group_ids = removed_roles.mapped("group_id.id")
        actual_group_ids = self.role_ids.mapped("group_id.id")
        return any(i in removed_group_ids for i in channel.group_ids.ids) and all(
            i not in actual_group_ids for i in channel.group_ids.ids
        )

    @api.onchange("role_line_ids")  # inverse
    def unsubscribe_from_mail_channel(self):
        self._origin.role_ids.filtered(lambda role: role not in self.role_ids)
        mail_channel_ids = (
            self.env["mail.channel"]
            .search([("public", "=", "private")])
            .filtered(self._filter_private_channel_removed_group)
            .mapped("id")
        )

        if mail_channel_ids:
            self.env["mail.channel.partner"].search(
                [
                    ("partner_id", "=", self.partner_id.id),
                    ("channel_id", "in", mail_channel_ids),
                ]
            ).unlink()
