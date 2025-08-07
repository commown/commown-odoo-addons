from odoo import api, models


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.model
    def _default_invoice_mail_template_id(self):
        "Inactivate default invoice_mail_template_id"
        return False

    @api.model
    def _default_pay_retry_mail_template_id(self):
        "Inactivate default pay_retry_mail_template_id"
        return False

    @api.model
    def _default_pay_fail_mail_template_id(self):
        "Inactivate default pay_fail_mail_template_id"
        return False

    @api.model
    def _default_auto_pay_retries(self):
        "Disable auto_pay_retries"
        return 0
