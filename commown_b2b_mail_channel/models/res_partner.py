from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    _sql_constraints = [
        ("mail_channel_uniq", "unique (mail_channel_id)", "Channel already used!"),
    ]

    mail_channel_id = fields.Many2one(
        "mail.channel",
        string="Support mail chanel",
        domain=[("public", "=", "private"), ("channel_type", "=", "channel")],
    )

    def write(self, vals):
        """Override write function to add/remove company's partners when support channel is modified."""
        if "mail_channel_id" in vals.keys():
            new_chan_id = vals["mail_channel_id"]
            if self.mail_channel_id and self.mail_channel_id.id != new_chan_id:
                self.remove_partners_from_channel(self.mail_channel_id, self.child_ids)

            if new_chan_id != False:
                partners_to_add = self.child_ids.filtered(
                    lambda p: p.company_type == "person" and p.user_ids
                )
                self.env["mail.channel"].browse(new_chan_id).channel_invite(
                    partners_to_add.ids
                )
        if not self.is_company and "parent_id" in vals.keys():
            new_parent_id = vals["parent_id"]
            if new_parent_id:
                new_parent = self.env["res.partner"].browse(new_parent_id)
                if new_parent.mail_channel_id:
                    new_parent.mail_channel_id.channel_invite(self.id)

                elif not new_parent.mail_channel_id and self.contract_ids.filtered(
                    lambda c: c.is_active_contract()
                ):
                    new_parent.sudo().create_mail_channel()

            if not new_parent_id:
                old_parent = self.parent_id
                if old_parent and old_parent.mail_channel_id:
                    self.remove_partners_from_channel(old_parent.mail_channel_id, self)

        return super().write(vals)

    def remove_partners_from_channel(self, channel, partners):
        self.env["mail.channel.partner"].search(
            [
                ("channel_id", "=", channel.id),
                ("partner_id", "in", partners.ids),
            ]
        ).unlink()

    def create_mail_channel(self):
        if self.is_company and not self.mail_channel_id:
            group_admin = self.env.ref("commown_user_groups.admin")
            group_support = self.env.ref("commown_user_groups.support")
            group_commercial = self.env.ref("commown_user_groups.commercial")
            self.mail_channel_id = self.env["mail.channel"].create(
                {
                    "name": self.compute_support_channel_name(),
                    "public": "private",
                    "company_id": self.id,
                }
            )
            # Remove the user that created the channel
            self.mail_channel_id.channel_last_seen_partner_ids.filtered(
                lambda cp: cp.partner_id == self.env.user.partner_id
            ).unlink()
            self.mail_channel_id.group_ids += (
                group_admin + group_commercial + group_support
            )

    def compute_support_channel_name(self):
        return " ".join(["Support", self.name])

    @api.constrains("name")
    def set_support_channel_name(self):
        if self.mail_channel_id:
            self.mail_channel_id.name = self.compute_support_channel_name()
