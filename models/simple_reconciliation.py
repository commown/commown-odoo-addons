from datetime import datetime
import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


def fast_to_dt(string_date):
    return datetime(*map(int, string_date.split('-')))


class CommownMassReconcileSimplePartner(models.TransientModel):
    _name = 'mass.reconcile.simple.partner_commown'
    _inherit = 'mass.reconcile.simple'
    _key_field = 'partner_id'
    max_reconcile_days_gap = 7

    @api.multi
    def rec_auto_lines_simple(self, lines):
        """ Same reconcile method as mass.reconcile.simple.partner but with a
        control of the maturity date gap between them: if the date difference
        is bigger than `max_reconcile_days_gap`, the moves won't be reconciled.
        """
        if self._key_field is None:
            raise ValueError("_key_field has to be defined")
        count = 0
        res = []
        _logger.info('Reconciling %s lines...', len(lines))
        while (count < len(lines)):
            date_1 = fast_to_dt(lines[count]['date_maturity'])
            if count and not count % 10:
                _logger.info('Reconcile progress: %s/%s', count, len(lines))
            for i in range(count + 1, len(lines)):
                if lines[count][self._key_field] != lines[i][self._key_field]:
                    break
                if self.max_reconcile_days_gap is not None:
                    gap = (fast_to_dt(lines[i]['date_maturity']) - date_1).days
                    if gap > self.max_reconcile_days_gap:
                        break
                check = False
                if lines[count]['credit'] > 0 and lines[i]['debit'] > 0:
                    credit_line = lines[count]
                    debit_line = lines[i]
                    check = True
                elif lines[i]['credit'] > 0 and lines[count]['debit'] > 0:
                    credit_line = lines[i]
                    debit_line = lines[count]
                    check = True
                if not check:
                    continue
                reconciled, dummy = self._reconcile_lines(
                    [credit_line, debit_line],
                    allow_partial=False
                    )
                if reconciled:
                    _logger.info('Reconcile success: %s <-> %s',
                                 lines[i]['id'], lines[count]['id'])
                    res += [credit_line['id'], debit_line['id']]
                    del lines[i]
                    break
            count += 1
        return res

    @api.multi
    def _simple_order(self, *args, **kwargs):
        return (
            "ORDER BY account_move_line.%s, "
            "account_move_line.date_maturity asc") % self._key_field

    def _base_columns(self):
        cols = super(CommownMassReconcileSimplePartner, self)._base_columns()
        cols.append('account_move_line.date_maturity')
        return cols
