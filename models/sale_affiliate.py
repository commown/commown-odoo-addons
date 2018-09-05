from dateutil.relativedelta import relativedelta
from datetime import date
from collections import OrderedDict
from copy import deepcopy

from odoo import models, fields, api
from odoo.tools.translate import html_translate


class SaleAffiliate(models.Model):
    _inherit = 'sale.affiliate'

    valid_sale_states = {'sent', 'sale', 'done'}

    gain_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ], default='percentage', string='Gain per sale value type')

    gain_value = fields.Float(string="Gain per sale Value")

    partner_description = fields.Html(
        'Description for affiliate partner\'s extranet',
        sanitize_attributes=False, translate=html_translate)

    def _gain_fixed(self, amount):
        return self.gain_value

    def _gain_percentage(self, amount):
        return amount * self.gain_value / 100.

    @api.multi
    def report_data(self, month_num=None):
        """ Return monthly statistics for current (single) affiliate, in
        chronological order, for each of the last `month_num` months
        from now (if not older than the affiliate's creation date).

        The returned value is an ordered dict with keys being the
        (chronologically ordered) months and values ordered dict which
        keys are the (alphabetically ordered) products (where all
        restricted products, if any, have an entry) and values are:

        - the initiated sale number
        - the validated sale number
        - the financial gain of the affiliate partner

        """
        self.ensure_one()

        domain = [('affiliate_id', '=', self.id)]
        if month_num is not None:
            oldest = (date.today().replace(day=1)
                      - relativedelta(months=month_num))
            domain.append(
                ('create_date', '>=', oldest.strftime(fields.DATETIME_FORMAT)),
            )
        requests = self.env['sale.affiliate.request'].search(domain)

        data = {}
        prod_item = {'initiated': 0, 'validated': 0, 'gain': 0.}

        month_item = {p.name: prod_item.copy()
                      for p in self.restriction_product_tmpl_ids}

        gain_func = getattr(self, '_gain_' + self.gain_type)

        for req in requests:
            for so in req.sale_ids:
                for ol in so.order_line:
                    if self._is_sale_order_line_qualified(ol):
                        month_data = data.setdefault(
                            so.create_date[:7],  # XXX month repr
                            deepcopy(month_item))
                        prod_name = ol.product_id.product_tmpl_id.name
                        prod_data = month_data.setdefault(prod_name,
                                                          prod_item.copy())
                        qty = int(ol.product_uom_qty)
                        prod_data['initiated'] += qty
                        if so.state in self.valid_sale_states:
                            prod_data['validated'] += qty
                            prod_data['gain'] = qty * gain_func(ol.price_unit)

        return OrderedDict([
            (month, OrderedDict([
                (product, data[month][product])
                for product in sorted(data[month])]))
            for month in sorted(data)])

    @api.multi
    def sales_currency(self):
        return self.env.ref('base.main_company').currency_id.symbol
