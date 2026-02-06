import logging
from urllib.parse import urlparse

from odoo.http import request, route

from odoo.addons.website_sale_affiliate.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class ShopRedirect(WebsiteSale):
    def _get_allowed_redirect_netlocs(self):
        param_netlocs = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("commown.allowed_redirect_netlocs")
        )

        return param_netlocs.split(",") if param_netlocs else []

    @route(["/shop/redirect"], type="http", auth="none", website=True)
    def shop_redirect(self, redirect="/", **kwargs):
        _logger.debug("shop redirect called redirect=%s, kwargs=%s", redirect, kwargs)
        local = True

        if redirect.startswith("http://") or redirect.startswith("https://"):
            allowed_netlocs = self._get_allowed_redirect_netlocs()

            if urlparse(redirect).netloc not in allowed_netlocs:
                redirect = "/shop"
                _logger.info("Redirecting spammer to %s", redirect)
                return request.redirect(redirect)
            local = False

        self._store_affiliate_info(**kwargs)
        return request.redirect(redirect, local=local)
