from odoo.addons.portal.controllers.portal import CustomerPortal


class FirstnameCustomerPortal(CustomerPortal):
    CustomerPortal.MANDATORY_BILLING_FIELDS.remove("name")
    CustomerPortal.MANDATORY_BILLING_FIELDS.extend(["firstname", "lastname"])
