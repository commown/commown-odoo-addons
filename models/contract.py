# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountAnalyticContract(models.Model):
    _inherit = 'account.analytic.contract'

    payment_mode_id = fields.Many2one(
        'account.payment.mode', string='Payment Mode',
        domain=[('payment_type', '=', 'inbound')],
    )

    min_contract_duration = fields.Integer(
        string='Min contract duration', default=0,
        help='Minimum contract duration in recurring interval unit',
    )


class AccountAnalyticContractLine(models.Model):
    _inherit = 'account.analytic.contract.line'

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        required=False,
        copy=False,
    )


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    min_contract_end_date = fields.Date(
        string='Min contract end date',
        compute='_compute_min_end_date', store=True,
    )

    @api.depends('date_start', 'min_contract_duration')
    def _compute_min_end_date(self):
        for record in self:
            date_delta = self.get_relative_delta(
                record.recurring_rule_type,
                record.min_contract_duration*record.recurring_interval)
            record.min_contract_end_date = fields.Date.from_string(
                record.date_start) + date_delta
