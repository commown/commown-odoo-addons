from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    _sql_constraints = [
        ("mail_channel_uniq", "unique (mail_channel_id)", "Channel already used!"),
    ]

    mail_channel_id = fields.Many2one(
        "mail.channel",
        string="Support mail channel",
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
        if "parent_id" in vals and not self.is_company:
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
            ref_roles_to_subscribe = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("commown_b2b_mail_channel.roles_subscribed_to_support_chan")
                .split(",")
            )
            groups_to_subscribe = self.env["res.groups"]
            for ref_role in ref_roles_to_subscribe:
                groups_to_subscribe += self.env.ref(ref_role).group_id

            self.mail_channel_id = self.env["mail.channel"].create(
                {
                    "name": " ".join(["Support", self.name]),
                    "public": "private",
                    "partner_company": self.id,
                }
            )
            self.mail_channel_id.group_ids += groups_to_subscribe

            # Remove the user that created the channel
            self.mail_channel_id.channel_last_seen_partner_ids.filtered(
                lambda cp: cp.partner_id == self.env.user.partner_id
            ).unlink()
            # Compute name
            self.set_support_channel_name()
