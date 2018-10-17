import logging

from odoo.http import request, route

from odoo.addons.website_sale_affiliate.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class ShopRedirect(WebsiteSale):

    @route(['/shop/redirect'], type='http', auth="none", website=True)
    def shop_redirect(self, redirect='/', **kwargs):
        _logger.debug('shop redirect called redirect=%s, kwargs=%s',
                      redirect, kwargs)
        self._store_affiliate_info(**kwargs)
        return request.redirect(redirect)
