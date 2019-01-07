# coding: utf-8

import logging
import traceback
from datetime import date
from StringIO import StringIO

import unicodecsv

from odoo import models, api, _, fields
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    STATEMENT_START_MAX_LINE = 10
    STATEMENT_START_MARKER = u'Solde en fin de période'
    STATEMENT_END_MARKER = u'Solde en début de période'
    ENCODING = 'latin1'
    _COLS = {
        'DATE': u'Date',
        'OP': u'Numéro d\'opération',
        'LABEL': u'Libellé',
        'CREDIT': u'Crédit',
        'DEBIT': u'Débit',
        'DETAIL': u'Détail',
    }

    def _get_line_amount(self, line):
        return self._parse_amount(
            line[self._COLS['CREDIT']] or line[self._COLS['DEBIT']])

    def _parse_amount(self, value):
        return float(value.replace(',', '.'))

    def _parse_date(self, value):
        day, month, year = map(int, value.split('/'))
        return date(2000+year, month, day).strftime(fields.DATE_FORMAT)

    def _get_credit_coop_importer(self, data):
        fobj = StringIO(data)
        start_line, end_amount = None, None
        for count, line in enumerate(fobj):
            line = line.decode(self.ENCODING)
            if count > self.STATEMENT_START_MAX_LINE:
                raise ValueError('Header not found')
            if line.startswith(self.STATEMENT_START_MARKER):
                start_line = line
                break
        reader = unicodecsv.DictReader(fobj, delimiter=';',
                                       encoding=self.ENCODING)
        assert set(reader.fieldnames).issuperset(self._COLS.values())
        if start_line is not None:
            index = reader.fieldnames.index(self._COLS['CREDIT'])
            end_amount = self._parse_amount(start_line.split(';')[index])
        return end_amount, reader

    @api.model
    def _parse_file(self, data_file):
        """ Import Crédit Coopération statement """
        try:
            end_amount, reader = self._get_credit_coop_importer(data_file)
        except:
            _logger.debug(
                'Could not interpret file as Credit Coop statement. Exception'
                ' raised. Traceback is :\n%s', traceback.format_exc())
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        statement = {
            'name': _('Crédit Coopération statement'),
            'transactions': [],
            'balance_end_real': end_amount,
        }

        for line in reader:
            num = reader.line_num
            if line[self._COLS['DATE']] == self.STATEMENT_END_MARKER:
                statement['balance_start'] = self._get_line_amount(line)
                continue

            try:
                statement['transactions'].append({
                    'date': self._parse_date(line[self._COLS['DATE']]),
                    'name': line[self._COLS['LABEL']],
                    'note': line[self._COLS['DETAIL']],
                    'unique_import_id': line[self._COLS['OP']],
                    'amount': self._get_line_amount(line),
                })
            except:
                _logger.error('Error importing line %d: %s\%s', num, line,
                              traceback.format_exc())
                raise UserError('Error importing line %d: %s' % (num, line))

        return 'EUR', None, [statement]
