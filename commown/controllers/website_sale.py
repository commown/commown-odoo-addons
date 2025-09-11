from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class CommownControllerWebsiteSale(WebsiteSale):
    @http.route()
    def product(self, product, category="", search="", **kwargs):
        result = super().product(product, category, search, **kwargs)
        result.qcontext["service_detail_url"] = (
            http.request.website.product_service_details_url
            or http.request.website.domain
        )
        return result
