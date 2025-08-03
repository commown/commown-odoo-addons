from odoo.addons.portal.controllers.portal import CustomerPortal


class FirstnameCustomerPortal(CustomerPortal):
    MANDATORY_BILLING_FIELDS = [
        field for field in CustomerPortal.MANDATORY_BILLING_FIELDS if field != "name"
    ] + ["firstname", "lastname"]
