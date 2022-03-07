import logging

from odoo import api, models, fields


_logger = logging.getLogger(__name__)


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    transaction_label = fields.Text(
        string='Payment label', default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #START#, #END#, #INV# (invoice number)'),
    )


class Contract(models.Model):
    _inherit = 'contract.contract'

    transaction_label = fields.Text(
        string='Payment label', default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #START#, #END#, #INV# (invoice number)'),
    )

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(Contract, record).name_get()[0]
            if record.contract_template_id:
                name += ' (%s)' % record.contract_template_id.name
            result.append((record.id, name))
        return result

    @api.multi
    def _pay_invoice(self, invoice):
        """ Insert custom payment transaction label into the context
        before executing the standard payment process. """
        if self.transaction_label:
            label = self._insert_markers(self.transaction_label)
            label = label.replace('#INV#', invoice.number)
            _logger.debug('Bank label for invoice %s: %s', invoice.number, label)
            self = self.with_context(slimpay_payin_label=label)
        return super(Contract, self)._pay_invoice(invoice)
