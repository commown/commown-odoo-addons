from odoo import fields, models, api


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    payment_mode_id = fields.Many2one(
        'account.payment.mode', string='Payment Mode',
        domain=[('payment_type', '=', 'inbound')],
    )

    @api.multi
    def main_product_line(self):
        self.ensure_one()
        lines = self.contract_line_ids
        return (
            lines.filtered(lambda l: '##PRODUCT##' in l.name) or
            sorted(lines, key=lambda l: l.price_unit)
        )[0]
