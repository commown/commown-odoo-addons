from odoo import _, fields, models


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

    disable_channel_subscription = fields.Boolean(
        "Disable automatic subscription to mail channel",
        default=False,
    )

    def has_to_be_subscribed_to_channel(self, mail_channel):
        """Return true if partner has to be subscribed to a given mail channel"""
        chan_partner = mail_channel.mapped("channel_last_seen_partner_ids.partner_id")
        return self not in chan_partner and self.user_ids

    def _update_subscription_on_user_creation(self):
        parent_mail_chan = self.parent_id.mail_channel_id
        if parent_mail_chan:
            if self.user_ids and self.has_to_be_subscribed_to_channel(parent_mail_chan):
                self.env["mail.channel.partner"].create(
                    {"partner_id": self.id, "channel_id": parent_mail_chan.id}
                )
            elif not self.user_ids:
                self.env["mail.channel.partner"].search(
                    [
                        ("partner_id", "=", self.id),
                        ("channel_id", "=", parent_mail_chan.id),
                    ]
                ).unlink()

    def _update_subscription_on_mail_channel_change(self, new_chan_id):
        if self.mail_channel_id and self.mail_channel_id.id != new_chan_id:
            self.mail_channel_id.remove_partners_but_employees()
        if new_chan_id and not self.disable_channel_subscription:

            new_chan = self.env["mail.channel"].browse(new_chan_id)
            new_chan.remove_partners_but_employees()

            chan_partner_to_create = [
                {"partner_id": p.id, "channel_id": new_chan_id}
                for p in self.child_ids
                if p.has_to_be_subscribed_to_channel(new_chan)
            ]
            self.env["mail.channel.partner"].create(chan_partner_to_create)

    def _update_subscription_on_parent_change(self, new_parent_id):
        if new_parent_id:
            new_parent = self.env["res.partner"].browse(new_parent_id)
            new_parent_chan = new_parent.mail_channel_id
            if (
                new_parent_chan
                and self.has_to_be_subscribed_to_channel(new_parent_chan)
                and not new_parent.disable_channel_subscription
            ):
                self.env["mail.channel.partner"].create(
                    {"partner_id": self.id, "channel_id": new_parent.mail_channel_id.id}
                )

            elif not new_parent_chan and self.contract_ids.filtered(
                lambda c: c.is_active_contract()
            ):
                new_parent.sudo().create_mail_channel()

        old_parent = self.parent_id
        if old_parent and old_parent.mail_channel_id:
            self.env["mail.channel.partner"].search(
                [
                    ("partner_id", "=", self.id),
                    ("channel_id", "=", old_parent.mail_channel_id.id),
                ]
            ).unlink()

    def write(self, vals):
        """Override write function to add/remove company's partners when support channel is modified."""
        if "mail_channel_id" in vals:
            self._update_subscription_on_mail_channel_change(vals["mail_channel_id"])
            self.set_support_channel_name(
                self.env["mail.channel"].browse(vals["mail_channel_id"])
            )

        if "parent_id" in vals and not self.is_company:
            self._update_subscription_on_parent_change(vals["parent_id"])

        result = super().write(vals)

        if "name" in vals:
            self.set_support_channel_name()

        return result

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
                    "name": "TEMP NAME",
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

    def set_support_channel_name(self, channel=None):
        channel = channel or self.mail_channel_id
        if channel:
            channel.with_context(lang="en_US").name = (
                "Support of company %s" % self.name
            )

            for lang, _lang_name in self.env["res.lang"].get_installed():
                if lang == "en_US":
                    continue
                context = {"lang": lang}  # Used below by _ (using python magic)
                channel.with_context(lang=lang).name = (
                    _("Support of company %s") % self.name
                )
