# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticContract(models.Model):
    _inherit = 'account.analytic.contract'

    payment_mode_id = fields.Many2one(
        'account.payment.mode', string='Payment Mode',
        domain=[('payment_type', '=', 'inbound')],
    )
