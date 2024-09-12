from odoo import fields, models


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
                self.env["mail.channel.partner"].search(
                    [
                        ("channel_id", "=", self.mail_channel_id.id),
                        ("partner_id", "in", self.child_ids.ids),
                    ]
                ).unlink()

            if new_chan_id != False:
                partners_to_add = self.child_ids.filtered(
                    lambda p: p.company_type == "person" and p.user_ids
                )
                self.env["mail.channel"].browse(new_chan_id).channel_invite(
                    partners_to_add.ids
                )
        return super().write(vals)

    def create_mail_channel(self):
        if self.is_company and not self.mail_channel_id:
            group_admin = self.env.ref("commown_user_groups.admin")
            group_support = self.env.ref("commown_user_groups.support")
            group_commercial = self.env.ref("commown_user_groups.commercial")
            self.mail_channel_id = self.env["mail.channel"].create(
                {
                    "name": " ".join(["Support", self.name]),
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
