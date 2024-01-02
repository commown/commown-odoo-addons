# Copyright 2018 Commown (https://commown.fr).
# @author Florent Cayré <florent@commown.fr>
# @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

from six import text_type

from odoo import fields, models

from odoo.addons.account_move_base_import.parser.file_parser import (
    FileParser,
    float_or_zero,
)

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    import_type = fields.Selection(selection_add=[("slimpay", "Slimpay")])


def _convert_date(value):
    return datetime(*map(int, value.split("-")))


def _int_or_none(value):
    try:
        return int(value)
    except ValueError:
        return None


class SlimpayParser(FileParser):
    def __init__(self, journal, ftype="csv", **kwargs):
        self.env = journal.env
        super(SlimpayParser, self).__init__(
            journal, ftype=ftype, extra_fields=self.conversion_dict, **kwargs
        )

    @classmethod
    def parser_for(cls, parser_name):
        return parser_name == "slimpay"

    conversion_dict = {
        "Libelle": text_type,
        "Nomdebiteur": text_type,
        "Datevaleur": _convert_date,
        "Creditvaleur": float_or_zero,
        "Debitvaleur": float_or_zero,
        "ReferenceClient": _int_or_none,
        "TransactionID": text_type,
        "OriginalTransactionID": text_type,
    }

    def _post(self, *args, **kwargs):
        """Remove all rows to be skipped:
        - the lines that do not represent a bank op (totals, comments, etc.)
        - the lines that have already been imported (to allow report overlaps)
        """
        # Proceed in line reverse order to remove rows in-place by index number
        initial_len = len(self.result_row_list)
        for num, row in enumerate(reversed(self.result_row_list)):
            if not row["CodeOP"]:
                del self.result_row_list[initial_len - num - 1]
        return super()._post(*args, **kwargs)

    def _get_partner_id(self, line):
        if line["CodeOP"].startswith("FEE-"):
            return self.journal.partner_id.id
        partner = self.env["res.partner"]
        _pid = line["ReferenceClient"]
        if _pid is not None:
            partner = partner.search([("id", "=", _pid)])
        if not partner and line["TransactionID"]:
            partner = (
                self.env["payment.transaction"]
                .search(
                    [
                        ("acquirer_reference", "=", line["TransactionID"]),
                    ]
                )
                .mapped("partner_id")
            )
        if len(partner) == 1:
            return partner.commercial_partner_id.id
        return False

    def _get_account_id(self, line):
        if line["CodeOP"].startswith("FEE-"):
            return self.journal.commission_account_id.id
        else:
            return self.journal.receivable_account_id.id

    def get_move_line_vals(self, line, *args, **kwargs):
        vals = {
            "name": line["Libelle"],
            "date_maturity": line["Datevaleur"],
            "credit": line["Creditvaleur"],
            "debit": line["Debitvaleur"],
            "already_completed": False,
            "partner_id": self._get_partner_id(line),
            "account_id": self._get_account_id(line),
        }
        _logger.debug("get_move_line_vals returns %s", vals)
        return vals
