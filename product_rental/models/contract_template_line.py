from odoo import fields, models


class ContractTemplateLine(models.Model):
    _inherit = 'contract.template.line'

    commitment_duration = fields.Integer(
        string='Commitment duration',
        help='Commitment duration in recurring interval unit',
    )
