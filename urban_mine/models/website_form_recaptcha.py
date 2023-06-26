from odoo import models


class WebsiteFormRecaptcha(models.AbstractModel):
    """Remplace recaptcha server-side API calls by hcaptcha"""

    _inherit = "website.form.recaptcha"

    URL = "https://api.hcaptcha.com/siteverify"
    RESPONSE_ATTR = "h-captcha-response"
