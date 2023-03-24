import logging

from odoo import _, http
from odoo.http import request

from odoo.addons.website_sale_payment_slimpay.controllers.main import (
    SlimpayControllerWebsiteSale,
)

_logger = logging.getLogger(__name__)


class CommownSlimpayController(SlimpayControllerWebsiteSale):
    @http.route(
        ["/payment/slimpay_transaction/<int:acquirer_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def payment_slimpay_transaction(self, acquirer_id):
        """This method reuses the partner's token unless the SEPA mandate
        product is in current sale order. Note this plays well with
        the `commown.payment` template (in website_sale_templates.xml)
        that hides the token choices from the user. This simplifies
        things for the user, which only sees one payment choice.
        """
        _logger.debug("Examine if partner's mandate can be reused...")

        so_id = request.session["sale_order_id"]
        so = request.env["sale.order"].sudo().browse(so_id)
        sepa_id = request.env.ref("commown.sepa_mandate").id

        reuse_token = bool(
            request.env.user.partner_id == so.partner_id
            and so.partner_id.payment_token_id
            and so.partner_id.payment_token_id.active
            and sepa_id not in so.mapped("order_line.product_id.product_tmpl_id").ids
        )

        if not reuse_token:
            _logger.info(
                "Token not reused: SEPA mandate found in the so"
                " or partner has no active token."
            )
            return super().payment_slimpay_transaction(acquirer_id)

        token = so.partner_id.payment_token_id
        _logger.info("Token %s reused!", token.id)

        transaction_id = request.session["__website_sale_last_tx_id"]
        transaction = request.env["payment.transaction"].browse(transaction_id)

        assert (
            not transaction.payment_token_id
            and token.partner_id == transaction.partner_id
        ), _("Incoherent transaction/token partners")

        transaction = transaction.sudo()
        transaction.payment_token_id = token
        transaction.slimpay_s2s_do_transaction()
        transaction._post_process_after_done()
        return "/shop/payment/validate"
