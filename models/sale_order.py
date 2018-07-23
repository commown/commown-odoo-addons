from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def generate_rental_contracts(self):
        EMPTY_DATE = '2030-01-01'

        for record in self:
            count = 0

            for so_line in record.order_line:
                product = so_line.product_id.product_tmpl_id
                if product.is_rental and product.rental_contract_tmpl_id:
                    count += 1
                    contract_tmpl = product.rental_contract_tmpl_id
                    contract = self.env['account.analytic.account'].create({
                        'name': '%s-%02d' % (record.name, count),
                        'partner_id': record.partner_id.id,
                        'recurring_invoices': True,
                        'contract_template_id': contract_tmpl.id,
                        'date_start': EMPTY_DATE,
                        'recurring_next_date': EMPTY_DATE,
                    })
                    contract._onchange_contract_template_id()
                    contract.update({'is_auto_pay': False})
