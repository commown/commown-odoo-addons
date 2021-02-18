import logging
from urlparse import urlparse

from odoo.http import request, route

from odoo.addons.website_sale_affiliate.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class ShopRedirect(WebsiteSale):

    @route(['/shop/redirect'], type='http', auth="none", website=True)
    def shop_redirect(self, redirect='/', **kwargs):
        _logger.debug('shop redirect called redirect=%s, kwargs=%s',
                      redirect, kwargs)
        if redirect.startswith("http://") or redirect.startswith("https://"):
            if not urlparse(redirect).netloc.endswith('commown.coop'):
                return request.redirect('/shop')
        self._store_affiliate_info(**kwargs)
        return request.redirect(redirect)
