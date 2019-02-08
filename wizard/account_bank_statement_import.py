# coding: utf-8

import logging
import traceback
from datetime import date
from StringIO import StringIO

import unicodecsv

from odoo import models, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'
    lanef_encoding = 'iso8859'
    lanef_months = {
        u'janv.': 1, u'févr.': 2, u'mars': 3, u'avr.': 4, u'mai': 5,
        u'juin': 6, u'juil.': 7, u'août': 8, u'sept.': 9, u'oct.': 10,
        u'nov.': 11, u'déc.': 12}

    def _lanef_parse_amount(self, line, colname=u'Montant'):
        return float(line[colname].replace(u',', u'.').replace(u' ', u''))

    def _lanef_parse_date(self, line, colname=u'Date Valeur'):
        day, month_name, year = line[colname].split()
        return date(int(year), self.lanef_months[month_name], int(day))

    def _get_lanef_importer(self, data):
        reader = unicodecsv.DictReader(
            StringIO(data), delimiter=',', encoding=self.lanef_encoding)
        assert set(reader.fieldnames).issuperset([
            u'Date Valeur', u'Référence',
            u'Montant', u'Solde', u'Libellé',
            ])
        return reader

    @api.model
    def _parse_file(self, data_file):
        """ Import La Nef CSV statement """
        try:
            reader = self._get_lanef_importer(data_file)
        except:
            _logger.debug(
                'Could not interpret file as La Nef statement. Exception'
                ' raised. Traceback is :\n%s', traceback.format_exc())
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        statement = {
            'name': _('La Nef statement'),
            'transactions': [],
        }

        min_date, min_date_line = None, None
        max_date, max_date_line = None, None
        for line in reader:
            num = reader.line_num
            amount = self._lanef_parse_amount(line)
            date = self._lanef_parse_date(line)
            try:
                statement['transactions'].append({
                    'date': date,
                    'name': line[u'Libellé'],
                    'amount': amount,
                    'note': line[u'Référence'],
                })
                if min_date_line is None or min_date > date:
                    min_date, min_date_line = date, line
                if max_date_line is None or max_date < date:
                    max_date, max_date_line = date, line
            except:
                _logger.error('Error importing line %d: %s\%s', num, line,
                              traceback.format_exc())
                raise UserError('Error importing line %d: %s' % (num, line))
        if min_date_line is not None:
            statement['balance_start'] = (
                self._lanef_parse_amount(min_date_line, u'Solde')
                - self._lanef_parse_amount(min_date_line, u'Montant'))
        if max_date_line is not None:
            statement['balance_end_real'] = self._lanef_parse_amount(
                max_date_line, u'Solde')
        return 'EUR', None, [statement]
