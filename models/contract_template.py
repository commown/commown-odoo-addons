from odoo import fields, models


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    payment_mode_id = fields.Many2one(
        'account.payment.mode', string='Payment Mode',
        domain=[('payment_type', '=', 'inbound')],
    )

    commitment_duration = fields.Integer(
        string='Commitment duration', default=0,
        help='Commitment duration in recurring interval unit',
    )
