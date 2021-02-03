from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class RentalProductWebsiteSale(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        result = super().product(product, category='', search='', **kwargs)
        contract_template = product.sudo().property_contract_template_id
        main = contract_template.main_product_line()
        rtypes = dict(main.fields_get()['recurring_rule_type']['selection'])
        result.qcontext.update({
            "main_contract_line": main,
            "recurring_rule_type": rtypes[main.recurring_rule_type].lower(),
            "rental_price_base": product.rental_price,
            "rental_price_ratio": product.rental_price_ratio(),
        })
        return result
