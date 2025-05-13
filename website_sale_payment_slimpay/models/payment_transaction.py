import logging
from urllib.parse import parse_qsl, urlparse

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        "This method returns the redirect form to Slimpay to actually pay"

        # An http form with GET as a method removes all "action" URL parameters
        # on submission, so we need to generate an input for each one:
        p_url = urlparse(self.approval_url())
        return {
            "action": f"{p_url.scheme}://{p_url.netloc}{p_url.path}",
            "inputs": parse_qsl(p_url.query),
        }
