from odoo import models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def alternative_send_shipping(self, pickings):
        """Prevent roulier shipping label generation on picking validation"""
        _self = self.with_context(is_roulier_return_false=True)
        return super(DeliveryCarrier, _self).alternative_send_shipping(pickings)

    def _is_roulier(self):
        "Return False when context contains a truthy 'is_roulier_return_false' value"
        if self.env.context.get("is_roulier_return_false", False):
            return False
        else:
            return super()._is_roulier()
