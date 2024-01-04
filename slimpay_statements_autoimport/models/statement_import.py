from base64 import b64encode
from datetime import date, timedelta
from urllib.parse import urlparse

import lxml
import requests

from odoo import _, api, fields, models
from odoo.tools.config import config

_LINK_TEXT = "télécharge"


class SlimpayStatementImport(models.Model):
    _name = "slimpay_statements_autoimport.statement_import"
    _description = "Slimpay statement import"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char("Email subject")
    mail_html = fields.Html("Email content", sanitize_attributes=False)
    imported_statement = fields.Many2one("account.move")

    def _get_token(self, api_url, login, password):
        auth = b64encode(b"dashboard:")
        resp = requests.post(
            "%s/oauth/token" % api_url,
            headers={"Authorization": "Basic %s" % auth.decode("utf-8")},
            data={
                "grant_type": "password",
                "username": login,
                "password": password,
                "scope": (
                    "https://apis.slimpay.net/auth/login"
                    "+https://apis.slimpay.net/auth/report"
                ),
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _get_int_param(self, name, default):
        pname = "slimpay_statements_autoimport." + name
        return int(self.env["ir.config_parameter"].get_param(pname, default))

    def _compute_reporting_dates(self, start_date):
        """Return suitable reporting start and end date as strings.

        Given import state date parameter is usually None (exceptions: first import and
        unittests), in which case the day after last slimpay move is taken, if any (or
        an error is raised).

        If no suitable dates are found because of following contraints, `None, None` is
        returned. Constraints are:

        - system parameter `import_only_older_days` and `import_duration_days` must be
          set and positive and strictly positive integers respectively

        - the imported data must be old (and thus reliable) enough; this is true if
          the import start date + import_duration_days

        """
        older_days = self._get_int_param("import_only_older_days", 0)
        duration_days = self._get_int_param("import_duration_days", 0)
        if older_days < 0 or duration_days <= 0:
            return None, None

        if start_date is None:
            journal = self.env.ref("slimpay_statements_autoimport.slimpay_journal")
            last_import = self.env["account.move"].search(
                [("journal_id", "=", journal.id)],
                order="date desc",
                limit=1,
            )

            if not last_import:
                raise_msg = _("Cannot determine a suitable slimpay import start date.")
                raise ValueError(raise_msg)

            start_date = last_import.date + timedelta(days=1)

        end_date = start_date + timedelta(duration_days)
        max_end_date = date.today() - timedelta(older_days)

        if end_date > max_end_date:
            return None, None

        return fields.Date.to_string(start_date), fields.Date.to_string(end_date)

    def _cron_reporting(self, start_date=None):
        "Cron that performs a reporting demand using web scraping"

        # Don't do anything if not configured or last import too recent
        conf = config.misc.get("slimpay_statements_autoimport")
        if conf is None:
            return

        start_date, end_date = self._compute_reporting_dates(start_date)
        if start_date is None:
            return

        slm = self.env.ref("account_payment_slimpay.payment_acquirer_slimpay")
        token = self._get_token(slm.slimpay_api_url, conf["login"], conf["password"])

        resp = requests.post(
            conf["reports_url"],
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer %s" % token,
                "Content-Type": "application/json",
            },
            json={
                "creditorReference": slm.slimpay_creditor,
                "startDate": start_date,
                "endDate": end_date,
                "type": "full",
                "locale": "fr",  # Important for csv column parsing!
            },
        )
        resp.raise_for_status()

    def _import_statement(self, fname, fbinary):
        "Import a Slimpay statement, update the importer, apply some data corrections"

        journal = self.env.ref("slimpay_statements_autoimport.slimpay_journal")
        importer = self.env["credit.statement.import"].create(
            {
                "journal_id": journal.id,
                "input_statement": b64encode(fbinary),
                "file_name": fname,
                "partner_id": journal.partner_id.id,
                "receivable_account_id": journal.receivable_account_id.id,
                "commission_account_id": journal.commission_account_id.id,
            }
        )
        action = importer.import_statement()

        self.imported_statement = action.get("res_id", False)
        self.name = self.imported_statement.ref

        # Set date to date_maturity for all imported move lines. Note that date is a
        # related field to the move's date with store=True, hence the SQL usage:
        self.env.cr.execute(
            "UPDATE account_move_line SET date=date_maturity WHERE move_id=%s",
            (self.imported_statement.id,),
        )
        self.imported_statement.env.cache.invalidate()

    def fetch_and_import_statement(self):
        "Find the download link in the email, fetch the csv file and import it"
        doc = lxml.html.fromstring(self.mail_html)
        urls = doc.xpath("//a[contains(text(), '%s')]/@href" % _LINK_TEXT)
        if len(urls) == 1:
            resp = requests.get(urls[0])
            if resp.status_code != 200:
                raise ValueError(
                    f"{resp.status_code} {resp.reason}\nResponse:\n{resp.text}"
                )
            else:
                fname = urlparse(urls[0]).path.rsplit("/", 1)[-1]
                self._import_statement(fname, resp.text.encode(resp.encoding))
        else:
            raise ValueError("Cannot find one download URL in the email")

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        "Store the email text and create a queue job to fetch and import it"
        custom_values = custom_values or {}
        custom_values["mail_html"] = msg_dict["body"]
        result = super().message_new(msg_dict, custom_values=custom_values)
        result.with_delay().fetch_and_import_statement()
        return result

    @api.multi
    def button_open_job(self):
        self.ensure_one()
        func_str = (
            "slimpay_statements_autoimport.statement_import(%s,)"
            ".fetch_and_import_statement()"
        )
        domain = [("func_string", "=", func_str % self.id)]
        job = self.env["queue.job"].search(domain, limit=1)
        if job:
            return {
                "name": _("Slimpay automatic import job"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "queue.job",
                "res_id": job.id,
            }
