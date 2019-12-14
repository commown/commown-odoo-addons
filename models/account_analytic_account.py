from dateutil.relativedelta import relativedelta

from odoo import api, models


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

    def _transaction_label_subtitutions(self, invoice):
        """ Return a dict {marker: value} mapping marker in the contract's
        transaction label attribute value to their real value.
        As of today, the returned markers are #START#, #END#, #INV#.
        """
        lang = self.env['res.lang'].search(
            [('code', '=', self.partner_id.lang)])
        date_format = lang.date_format or '%m/%d/%Y'
        if self.recurring_invoicing_type == 'pre-paid':
            date_from = self.env.context['old_date']
            date_to = self.env.context['next_date'] - relativedelta(days=1)
        else:
            date_from = (
                self.env.context['old_date'] -
                self.get_relative_delta(self.recurring_rule_type,
                                        self.recurring_interval) +
                relativedelta(days=1))
            date_to = self.env.context['old_date']
        return {
            '#INV#': invoice.number,
            '#START#': date_from.strftime(date_format),
            '#END#': date_to.strftime(date_format),
        }

    @api.multi
    def _pay_invoice(self, invoice):
        """ Insert custom payment transaction label into the context
        before executing the standard payment process. """
        if (self.transaction_label
                and 'old_date' in self.env.context
                and 'next_date' in self.env.context):
            label = self.transaction_label
            for k, v in self._transaction_label_subtitutions(invoice).items():
                label = label.replace(k, v)
            self = self.with_context(slimpay_payin_label=label)
        return super(AccountAnalyticAccount, self)._pay_invoice(invoice)
