from odoo.addons.website_sale.controllers.main import WebsiteSale


class CommownControllerWebsiteSale(WebsiteSale):
    def _get_mandatory_shipping_fields(self):
        fields = super()._get_mandatory_billing_fields()
        if "email" not in fields:
            fields.append("email")
        return fields
