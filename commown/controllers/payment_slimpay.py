import logging

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.website_sale.controllers.main import PaymentPortal

_logger = logging.getLogger(__name__)


class CommownPaymentPortal(PaymentPortal):
    def _create_transaction(self, *args, **kwargs):
        tx_sudo = super()._create_transaction(*args, **kwargs)
        if tx_sudo.state == "done":
            tx_sudo._finalize_post_processing()
        return tx_sudo

    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """This method reuses the partner's token unless the SEPA mandate
        product is in current sale order. Note this plays well with
        the `commown.payment` template (in website_sale_templates.xml)
        that hides the token choices from the user. This simplifies
        things for the user, which only sees one payment choice.
        """
        _logger.debug("Examine if partner's mandate can be reused...")

        env = request.env

        try:
            so_sudo = self._document_check_access("sale.order", order_id, access_token)
        except MissingError as error:
            raise error
        except AccessError as error:
            raise ValidationError(_("The access token is invalid.")) from error
        sepa = env.ref("commown.sepa_mandate")

        token_sudo = so_sudo.partner_id.payment_token_id
        reuse_token = bool(
            token_sudo
            and token_sudo.active
            and sepa not in so_sudo.mapped("order_line.product_id.product_tmpl_id")
        )
        if not reuse_token:
            _logger.info(
                "Token not reused: SEPA mandate found in the so"
                " or partner has no active token."
            )
        else:
            kwargs.update({"flow": "token", "payment_option_id": token_sudo.id})
            _logger.info("Token %s reused!", token_sudo.id)

        result = super().shop_payment_transaction(order_id, access_token, **kwargs)

        if reuse_token:
            tx = env["payment.transaction"].browse(
                request.session["__website_sale_last_tx_id"]
            )
            if tx.state == "done":
                # Since the shop_payment_transaction adds a polling process
                # for the newly generated transaction, meant to be checked
                # by the Javascript code asynchronously, and paying a Slimpay tx
                # with a reused token immediately returns a response, we remove
                # the transaction from the list of monitored transactions.
                PaymentPostProcessing.remove_transactions(tx)

                # Since this transaction was considered as 'redirect' from a third-party provider (Slimpay),
                # the JS program of the payment module expects a redirect_form_html template to render the third-party page.
                # If the token was reused, and the payment succeeded, then we only need to redirect to the validation page.
                redirect_form_view = tx.provider_id._get_redirect_form_view()
                if redirect_form_view:
                    redirect_form_html = env["ir.qweb"]._render(
                        redirect_form_view.id, {"action": "/shop/payment/validate"}
                    )
                    result.update(redirect_form_html=redirect_form_html)

        return result
