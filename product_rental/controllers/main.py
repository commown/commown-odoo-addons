from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class RentalProductWebsiteSale(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        result = super().product(product, category='', search='', **kwargs)
        ct = product.sudo().property_contract_template_id
        rtypes = dict(ct.fields_get()['commitment_period_type']['selection'])
        result.qcontext.update({
            "commitment_period": {
                "number": ct.commitment_period_number,
                "type": rtypes[ct.commitment_period_type].lower(),
            },
            "rental_price_base": product.rental_price,
            "rental_price_ratio": product.rental_price_ratio(),
        })
        return result
