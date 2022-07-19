import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class CommownMassReconcileSimplePartner(models.TransientModel):
    _name = 'mass.reconcile.simple.partner_commown'
    _inherit = 'mass.reconcile.simple'
    _key_field = 'partner_id'
    default_max_reconcile_days_gap = 7
    default_max_reconcile_lines = 100

    @api.multi
    def rec_auto_lines_simple(self, lines):
        """ Same reconcile method as mass.reconcile.simple.partner but with a
        control of the maturity date gap between them: if the date difference
        is bigger than `max_reconcile_days_gap`, the moves won't be reconciled.
        """

        max_reconcile_days_gap = self.env.context.get(
            'max_reconcile_days_gap', self.default_max_reconcile_days_gap)
        _logger.info('max_reconcile_days_gap is %s', max_reconcile_days_gap)
        max_reconcile_lines = self.env.context.get(
            'max_reconcile_lines', self.default_max_reconcile_lines)
        _logger.info('max_reconcile_lines is %s', max_reconcile_lines)

        if self._key_field is None:
            raise ValueError("_key_field has to be defined")
        count = 0
        success_count = 0
        res = []
        _logger.info('Reconciling %s lines...', len(lines))
        while (count < len(lines)
               and success_count < max_reconcile_lines):
            date_1 = lines[count]['date_maturity']
            if count and not count % 10:
                _logger.info('Reconcile progress: %s/%s', count, len(lines))
            for i in range(count + 1, len(lines)):
                if lines[count][self._key_field] != lines[i][self._key_field]:
                    _logger.info('Stop searching - %d trial(s)'
                                 ' (key field changed)', i - count)
                    break
                if max_reconcile_days_gap is not None:
                    gap = (lines[i]['date_maturity'] - date_1).days
                    if gap > max_reconcile_days_gap:
                        _logger.info('Stop searching - %d trial(s)'
                                     ' (date gap reached)', i - count)
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
                    allow_partial=False)
                if reconciled:
                    _logger.info('Reconcile success: %s <-> %s - %d trial(s)',
                                 lines[i]['id'], lines[count]['id'], i - count)
                    res += [credit_line['id'], debit_line['id']]
                    del lines[i]
                    success_count += 1
                    break
            else:
                _logger.info('Tried all %d lines but no match found',
                             len(lines) - count)
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
