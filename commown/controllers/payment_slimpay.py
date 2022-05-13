import logging

from odoo import http
from odoo.http import request

from odoo.addons.website_sale_payment_slimpay.controllers.main \
    import SlimpayControllerWebsiteSale


_logger = logging.getLogger(__name__)


class CommownSlimpayController(SlimpayControllerWebsiteSale):

    @http.route(['/payment/slimpay_transaction/<int:acquirer_id>'],
                type='json', auth="public", website=True)
    def payment_slimpay_transaction(
            self, acquirer_id, tx_type='form', token=None, **kwargs):
        """This method reuses the partner's token unless the SEPA mandate
        product is in current sale order. Note this plays well with
        the `commown.payment` template (in website_sale_templates.xml)
        that hides the token choices from the user. This simplifies
        things for the user, which only sees one payment choice.
        """
        _logger.debug("Examine if partner's mandate can be reused...")
        if not token:  # an empty string in v12 (was None in v10...)
            so = request.env['sale.order'].sudo().browse(
                request.session['sale_order_id'])
            sepa_id = request.env.ref('commown.sepa_mandate').id
            if (so.partner_id.payment_token_id
                and sepa_id not in so.mapped(
                    'order_line.product_id.product_tmpl_id').ids):
                token = so.partner_id.payment_token_id.id
                _logger.info("Token %s reused!", token)
            else:
                _logger.info("Token not reused: SEPA mandate found in the so")
        return super(
            CommownSlimpayController, self).payment_slimpay_transaction(
                acquirer_id, tx_type=tx_type, token=token, **kwargs)
