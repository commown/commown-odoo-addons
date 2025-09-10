from odoo import api, models


class Contract(models.AbstractModel):
    _inherit = "contract.abstract.contract"

    @api.model
    def _default_invoice_mail_template_id(self):
        "Disable by default invoice_mail_template_id"
        return False

    @api.model
    def _default_pay_retry_mail_template_id(self):
        "Disable by default pay_retry_mail_template_id"
        return False

    @api.model
    def _default_pay_fail_mail_template_id(self):
        "Disable by default pay_fail_mail_template_id"
        return False

    @api.model
    def _default_auto_pay_retries(self):
        "Disable by default auto_pay_retries"
        return 0
