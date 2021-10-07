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
    lanef_encoding = 'utf-8'
    lanef_months = {
        u'janv.': 1, u'févr.': 2, u'mars': 3, u'avr.': 4, u'mai': 5,
        u'juin': 6, u'juil.': 7, u'août': 8, u'sept.': 9, u'oct.': 10,
        u'nov.': 11, u'déc.': 12}
    lanef_max_header_char_num = 1000
    lanef_expected_fieldnames = frozenset((
        u'Date de valeur', u'ID', u'Débit', u'Crédit', u'Libellé'))
    lanef_delimiter = ';'

    def _lanef_parse_amount(self, line):
        colname, sign = u'Crédit', 1
        if line[u'Crédit'] == u'':
            colname, sign = u'Débit', -1
        return float(line[colname]) * sign

    def _lanef_parse_date(self, line, colname=u'Date de valeur'):
        day, month, year = line[colname].split(u'/')
        return date(int(year), int(month), int(day))

    def _get_lanef_importer(self, data):
        f = StringIO(data)
        while f.pos < self.lanef_max_header_char_num:
            reader = unicodecsv.DictReader(
                f, delimiter=self.lanef_delimiter, encoding=self.lanef_encoding)
            if frozenset(reader.fieldnames).issuperset(
                    self.lanef_expected_fieldnames):
                return reader
        raise ValueError('Could not find suitable csv content for La Nef.')

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

        for line in reader:
            num = reader.line_num
            amount = self._lanef_parse_amount(line)
            date = self._lanef_parse_date(line)
            try:
                statement['transactions'].append({
                    'date': date,
                    'name': line[u'Libellé'],
                    'amount': amount,
                    'note': line[u'ID'],
                })
            except:
                _logger.error('Error importing line %d: %s\%s', num, line,
                              traceback.format_exc())
                raise UserError('Error importing line %d: %s' % (num, line))
        return 'EUR', None, [statement]
