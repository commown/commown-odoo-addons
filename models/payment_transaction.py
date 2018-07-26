import logging
from odoo import _, api, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _confirm_so(self, acquirer_name=False):
        """ This override should not be necessary, but is consequence of our
        usage of the sale order status 'sent', which is the final stage of our
        online rental sale process (for some probably bad reasons, to be deeply
        analysed soon, as of July 2018).
        """
        for tx in self:
            so = tx.sale_order_id
            if so and so.state in ['draft', 'sent']:
                if float_compare(tx.amount, so.amount_total, 2) == 0:
                    so.confirm_coupons()
        return super(PaymentTransaction, self)._confirm_so(acquirer_name)
