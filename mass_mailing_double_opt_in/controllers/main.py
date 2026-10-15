from odoo import http
from odoo.http import Controller, request


class DoubleOptInController(Controller):
    @http.route(
        "/newsletter/confirm_subscription", type="http", auth="public", website="True"
    )
    def confirm_newsletter_subscription(self, sign=""):
        env = request.env
        res_tmpl_id = "mass_mailing_double_opt_in.confirm"

        try:
            email, list_id = sign.split("|")

            # Fetch mailing list, raising a Value Error if invalid
            list_id = int(list_id)
            mail_list = env["mailing.list"].browse(list_id).exists().ensure_one()
        except ValueError:
            values_err_msg = _("The provided confirmation values were invalid.")
            return request.render(res_tmpl_id, {"err_msg": values_err_msg})

        ContactSudo = env["mailing.contact"].sudo()

        # Creating the mailing contact
        ContactSudo.with_context(default_list_ids=mail_list.ids).create(
            {"email": email}
        )

        return request.render(res_tmpl_id, {"email": email})
