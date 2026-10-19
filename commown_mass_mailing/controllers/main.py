from odoo import _, http
from odoo.http import request
from odoo.tools import email_normalize

from odoo.addons.mass_mailing_double_opt_in.controllers import main


class CommownMassMailingController(main.MassMailingDoubleOptInController):
    @http.route()
    def request_newsletter_subscription(self, email, list_id):
        env = request.env
        list_generic = env.ref("commown_mass_mailing.newsletter_generic")

        if list_id == list_generic.id:
            list_customers = env.ref("commown_mass_mailing.newsletter_customers")
            email_normalized = email_normalize(email)
            existing_contact = env["mailing.contact"].search_count(
                [("list_ids", "=", list_customers.id), ("email", "=", email_normalized)]
            )
            if existing_contact:
                return {
                    "result": "NOK",
                    "msg": _("You're already subscribed to the customer newsletter!"),
                }

        return super().request_newsletter_subscription(email, list_id)
