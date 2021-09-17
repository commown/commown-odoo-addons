import logging
import urllib

from odoo.http import request, route

from odoo.addons.website_sale_affiliate.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class ShopRedirect(WebsiteSale):

    @route(['/shop/redirect'], type='http', auth="none", website=True)
    def shop_redirect(self, redirect='/', **kwargs):
        _logger.debug('shop redirect called redirect=%s, kwargs=%s',
                      redirect, kwargs)
        if redirect.startswith("http://") or redirect.startswith("https://"):
            if not urllib.parse(redirect).netloc.endswith('commown.coop'):
                redirect = "/shop"
                _logger.info('Redirecting spammer to %s', redirect)
                return request.redirect(redirect)
        self._store_affiliate_info(**kwargs)
        return request.redirect(redirect)
