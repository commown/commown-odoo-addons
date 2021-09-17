import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = 'contract.contract'

    transaction_label = fields.Text(
        string='Payment label', required=True, default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #INV# (invoice number), #DATE# (invoice date)'),
    )

    def name_get(self):
        result = []
        for record in self:
            _id, name = super().name_get()[0]
            if record.contract_template_id:
                name += u' (%s)' % record.contract_template_id.name
            result.append((record.id, name))
        return result

    @api.multi
    def _pay_invoice(self, invoice):
        """ Insert custom payment transaction label into the context
        before executing the standard payment process. """
        if self.transaction_label:
            label = self.transaction_label.replace('#INV#', invoice.number)
            if "#DATE#" in label:
                lang = self.env['res.lang'].search(
                    [('code', '=', self.partner_id.lang)]
                )
                date_format = lang.date_format or '%m/%d/%Y'
                label = label.replace(
                    '#DATE#', invoice.date_invoice.strftime(date_format))
            _logger.debug('Bank label for invoice %s: %s',
                          invoice.number, label)
            self = self.with_context(slimpay_payin_label=label)
        return super()._pay_invoice(invoice)
