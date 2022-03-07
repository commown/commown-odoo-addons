import logging

from dateutil.relativedelta import relativedelta

from odoo import api, models


_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(AccountAnalyticAccount, record).name_get()[0]
            if record.contract_template_id:
                name += u' (%s)' % record.contract_template_id.name
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
        return super(AccountAnalyticAccount, self)._pay_invoice(invoice)
