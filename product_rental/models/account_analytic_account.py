import logging

from odoo import api, models, fields
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)

CONTRACT_PROD_MARKER = '##PRODUCT##'
CONTRACT_ACCESSORY_MARKER = '##ACCESSORY##'


class ProductRentalAccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

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

    def amount(self):
        """Compute the sum of contract line price that have no formula or a
        formula marked with '[DE]' (for 'commitment duration' in french).
        """
        self.ensure_one()
        return sum(self.recurring_invoice_line_ids.filtered(lambda l: (
            l.qty_type != 'variable' or u'[DE]' in l.qty_formula_id.name
        )).mapped('price_subtotal'))

    @api.multi
    def _convert_contract_lines(self, contract):
        """Extend contract functionalities: have ability to gather a main
        rental product and its (also rented) accessories on the same
        contract.

        This is done using dedicated markers (##PRODUCT## and
        ##ACCESSORY##) in recurring invoice line names. Those lines
        will be used as templates: the marker in the name is replaced
        by the name of the corresponding article, the quantity is set
        to 1 and the price set to the rental price of the product.
        """
        new_lines = super(ProductRentalAccountAnalyticAccount,
                          self)._convert_contract_lines(contract)

        sale_context = self.env.context.get('contract_from_so')
        if not sale_context:
            return new_lines

        contract_lines = []
        rental_products = {
            CONTRACT_PROD_MARKER: [
                (sale_context['main_product'], sale_context['main_so_line'], 1)
            ],
            CONTRACT_ACCESSORY_MARKER: sale_context['accessories'],
        }

        _logger.debug('rental_products: %s', rental_products)

        for new_line in new_lines:
            for marker, products in rental_products.items():
                if marker in new_line[2]['name']:
                    for product, so_line, qtty in products:
                        vals = new_line[2].copy()
                        rental_taxes = self.env['product.product'].browse(
                            vals['product_id']).taxes_id
                        vals.update({
                            'name': vals['name'].replace(
                                marker, product.name),
                            'specific_price': so_line.compute_rental_price(
                                rental_taxes),
                            'qtty': qtty,
                            'sale_order_line_id': so_line.id,
                        })
                        vals['display_name'] = vals['name']
                        # avoid inverse price computation
                        if 'price_unit' in vals:
                            del vals['price_unit']
                        contract_lines.append((0, 0, vals))
                    break
            else:
                new_line[2]['sale_order_line_id'] = sale_context[
                    'main_so_line'].id
                contract_lines.append(new_line)

        return contract_lines

    def button_open_sales(self):
        sales = self.mapped(
            'recurring_invoice_line_ids.sale_order_line_id.order_id')
        result = {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'domain': [('id', 'in', sales.ids)],
            'name': _('Related sales'),
        }
        if len(sales) == 1:  # single sale: display it directly
            views = [(False, 'form')]
            result['res_id'] = sales.id
        else:  # display a list
            views = [(False, 'list'), (False, 'form')]
        result['views'] = views
        return result
