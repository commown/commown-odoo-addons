from odoo import http
from odoo.http import request

from odoo.addons.payment_slimpay.controllers.main import SlimpayController


class CommownSlimpayController(SlimpayController):

    @http.route(['/payment/slimpay_transaction/<int:acquirer_id>'],
                type='json', auth="public", website=True)
    def payment_slimpay_transaction(
            self, acquirer_id, tx_type='form', token=None, **kwargs):
        if token is None:
            so = request.env['sale.order'].sudo().browse(
                request.session['sale_order_id'])
            sepa_id = request.env.ref('commown.sepa_mandate').id
            if sepa_id not in so.mapped(
                    'order_line.product_id.product_tmpl_id').ids:
                token = so.partner_id.payment_token_id.id
        return super(
            CommownSlimpayController, self).payment_slimpay_transaction(
                acquirer_id, tx_type=tx_type, token=token, **kwargs)
