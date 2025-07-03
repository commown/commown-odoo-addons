import json

from odoo import _, http
from odoo.http import request

from odoo.addons.website.controllers.form import WebsiteForm


class UrbanMineWebsiteForm(WebsiteForm):
    @http.route(type="http")
    def website_form(self, model_name, **kwargs):
        """Adds website_recaptcha_v2 verification to the urban mine form."""
        result, err_msg = request.website.is_recaptcha_v2_valid(request.params.copy())
        if result:
            return super().website_form(model_name, **kwargs)
        return json.dumps(
            {"error": _("Captcha failed for the following reason: %s", err_msg)}
        )
