from odoo import fields, models

from .slimpay_utils import SlimpayClient


class PaymentProviderSlimpay(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("slimpay", "Slimpay")],
        ondelete={"slimpay": "set default"},
    )
    slimpay_api_url = fields.Char(
        "API base url", required_if_provider="slimpay", groups="base.group_user"
    )
    slimpay_creditor = fields.Char(
        "Creditor reference",
        size=64,
        required_if_provider="slimpay",
        groups="base.group_user",
    )
    slimpay_app_id = fields.Char(
        "OAuth application Id",
        size=64,
        required_if_provider="slimpay",
        groups="base.group_user",
    )
    slimpay_app_secret = fields.Char(
        "OAuth application Secret",
        size=64,
        required_if_provider="slimpay",
        groups="base.group_user",
    )

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "slimpay").update(
            {
                "support_refund": "partial",
                "support_express_checkout": True,
                "support_tokenization": True,
            }
        )
        return

    def slimpay_client(self):
        return SlimpayClient(
            self.slimpay_api_url,
            self.slimpay_creditor,
            self.slimpay_app_id,
            self.slimpay_app_secret,
        )
