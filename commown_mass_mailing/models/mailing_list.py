from odoo import _, models
from odoo.tools import email_normalize


class CommownMailingList(models.Model):
    _inherit = "mailing.list"

    # pylint: disable=missing-return
    def action_sync(self):
        super().action_sync()
        if self == self.env.ref("commown_mass_mailing.newsletter_customers"):
            self._exclude_customers_from_generic_list()

    def _exclude_customers_from_generic_list(self):
        list_generic = self.env.ref("commown_mass_mailing.newsletter_generic")
        list_customers = self.env.ref("commown_mass_mailing.newsletter_customers")

        self.env.cr.execute(
            """
            DELETE FROM mailing_contact_list_rel AS mcl1
            WHERE mcl1.list_id = %(list_generic_id)s
            AND EXISTS (
                SELECT 1
                FROM mailing_contact_list_rel AS mcl2
                WHERE
                    mcl1.contact_id = mcl2.contact_id
                    AND mcl2.list_id = %(list_customers_id)s
            )""",
            {
                "list_generic_id": list_generic.id,
                "list_customers_id": list_customers.id,
            },
        )

    def request_newsletter_subscription(self, email):
        list_generic = self.env.ref("commown_mass_mailing.newsletter_generic")

        if self == list_generic:
            list_customers = self.env.ref("commown_mass_mailing.newsletter_customers")
            email_normalized = email_normalize(email)
            existing_contact = self.env["mailing.contact"].search_count(
                [("list_ids", "=", list_customers.id), ("email", "=", email_normalized)]
            )
            if existing_contact:
                subject = _("Subscription already completed")
                message_body = self.env["ir.qweb"]._render(
                    "mass_mailing_double_opt_in.already_subscribed_email"
                )
                self._send_newsletter_confirm_email(
                    email_normalized,
                    subject,
                    message_body,
                )
                return {
                    "result": "OK",
                    "msg": _(
                        "You will receive a mail shortly to confirm your subscription!"
                    ),
                }

        return super().request_newsletter_subscription(email)
