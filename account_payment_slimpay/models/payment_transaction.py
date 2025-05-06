import logging

from coreapi.exceptions import ErrorMessage

from odoo import _, models
from odoo.exceptions import ValidationError

from . import slimpay_utils

_logger = logging.getLogger(__name__)


class SlimpayTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "slimpay" or len(tx) == 1:
            return tx

        ref = notification_data.get("reference")
        tx = self.search([("reference", "=", ref), ("provider_code", "=", "slimpay")])
        if not tx:
            raise ValidationError(_("No transaction found matching reference %s.", ref))
        return tx

    def _process_notification_data(self, notification_data):
        """The posted data is validated using a http request to slimpay's
        server (to make sure posted data has not been forged), then the
        transaction status is updated.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != "slimpay":
            return

        if self.state == "done":
            _logger.debug("Transaction %r is already completed!", self.reference)
            return

        url = notification_data["_links"]["self"]["href"]
        client = self.provider_id.slimpay_client()
        doc = client.get(url)
        _logger.info("Slimpay corresponding order doc: %s", doc)
        assert doc["reference"] == self.reference

        slimpay_state = doc["state"]
        tx_attrs = {"provider_reference": doc["id"]}
        if slimpay_state == "closed.completed":
            self._slimpay_tx_completed(client, doc, **tx_attrs)
            return True
        elif slimpay_state.startswith("closed.aborted"):
            self._set_canceled()
        else:  # pragma: no cover
            # Should never happen
            self._set_pending()
        self.write(tx_attrs)
        return False

    def _slimpay_tx_completed(self, client, order_doc, **tx_attrs):
        _logger.info("Trying to complete transaction id %s", self.id)
        self.write(tx_attrs)
        # Confirm sale if necessary
        _logger.info("Setting sale transaction as done...")
        self._set_done()
        self._reconcile_after_done()  #
        self._finalize_post_processing()
        # Use mandate as a token for later automatic payments
        partner = self.partner_id
        _logger.info("Fetching new partner's mandate...")
        mandate_doc = client.get_from_doc(order_doc, "get-mandate")
        mandate_id = mandate_doc["id"]
        bank_account_doc = client.get_from_doc(mandate_doc, "get-bank-account")
        token_name = "IBAN %s (%s)" % (
            bank_account_doc["iban"],
            bank_account_doc["institutionName"],
        )
        token = self.env["payment.token"].create(
            {
                "payment_details": token_name,
                "partner_id": partner.id,
                "provider_id": self.provider_id.id,
                "provider_ref": mandate_id,
            }
        )
        token.transaction_ids |= self
        _logger.info("Added token id %s for %s", token.id, token.payment_details)
        return token

    def _is_out_transaction(self):
        self.ensure_one()
        payment = self.payment_id
        return bool(payment) and payment.payment_type == "outbound"

    def _label(self):
        """Try hard to return a useful label, using:
        - the 'slimpay_payin_label' of the context, if any
        - the `ref` field of the payment found in the transaction's payment, if any
        - the `reference` field of current transaction, if not empty
        - 'TR%d' % self.id as a last resort.
        """
        context = self.env.context
        if "slimpay_payin_label" in context:
            return context["slimpay_payin_label"]
        else:
            payment = self.payment_id
            if payment and payment.ref:
                return payment.ref
            return self.reference or "TR%d" % self.id

    def _send_payment_request(self):
        """Perform a payment through a server to server call using a previously
        signed mandate.
        """
        _logger.debug("Starting auto Slimpay Transaction TR%s...", self.id)
        client = self.provider_id.slimpay_client()
        mandate_ref = client.action(
            "GET", "get-mandates", params={"id": self.token_id.provider_ref}
        )["reference"]
        _logger.debug("Found mandate reference: %s", mandate_ref)
        amount = round(self.amount, self.currency_id.decimal_places)

        with self.env.cr.savepoint():
            err_msg = None
            try:
                provider_reference = client.create_payment(
                    mandate_ref,
                    amount,
                    self.currency_id.name,
                    self._label(),
                    out=self._is_out_transaction(),
                )
                _logger.debug("Payment creation result: %s", provider_reference)
            except ErrorMessage as exc:
                err_msg = _(exc)

        if err_msg is not None:
            self.update({"state": "error", "state_message": err_msg})
        else:
            self.update(
                {
                    "state": "done" if provider_reference else "error",
                    "provider_reference": provider_reference,
                }
            )

    def approval_url(self, so=None):
        "Return Slimpay approval URL for given optional sale order (1st one by default)"
        self.ensure_one()

        so = so or self.sale_order_ids[0]
        assert (
            self.env.user.partner_id.commercial_partner_id
            == so.partner_id.commercial_partner_id
        )

        base_url = self.env["website"].get_current_website().domain or self.env[
            "ir.config_parameter"
        ].get_param("web.base.url")

        approval_url = self.provider_id.slimpay_client().approval_url(
            self.reference,
            so.id,
            (so.partner_id.lang or "en_US").split("_")[0],
            so.amount_total,
            so.currency_id.name,
            so.currency_id.decimal_places,
            slimpay_utils.subscriber_from_partner(so.partner_id),
            base_url + self.landing_route,
        )
        _logger.debug(
            "Approval URL for transaction reference %(ref)s: %(url)s",
            {"url": approval_url, "ref": self.reference},
        )

        return approval_url
