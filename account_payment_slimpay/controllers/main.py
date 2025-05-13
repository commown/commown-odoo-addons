import json
import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class SlimpayController(http.Controller):
    @http.route(
        ["/payment/slimpay/s2s/feedback"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def feedback(self):
        """Controller called by slimpay once the customer has finished the
        checkout process. Performs basic checks then delegates to the provider.
        """
        post = json.loads(request.httprequest.data.decode("utf-8"))
        _logger.debug("slimpay feedback, post=%s", post)

        pt_model_sudo = request.env["payment.transaction"].sudo()
        try:
            tx_sudo = pt_model_sudo._handle_notification_data("slimpay", post)
        except ValidationError:
            _logger.warning("Enable to find 1 transaction from posted data %s", post)
            return Response("Incorrect transaction reference", status=200)

        if tx_sudo.state != "done":
            _logger.warning("Invalid feedback for transaction %r", tx_sudo.reference)
            return Response("Invalid feedback for order", status=200)

        return Response("OK", status=200)
