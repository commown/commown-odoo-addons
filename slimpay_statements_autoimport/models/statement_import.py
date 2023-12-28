from base64 import b64encode
from urllib.parse import urlparse

import lxml
import requests

from odoo import _, api, fields, models

_LINK_TEXT = "télécharge"


class SlimpayStatementImport(models.Model):
    _name = "slimpay_statements_autoimport.statement_import"
    _description = "Slimpay statement import"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char("Email subject")
    mail_html = fields.Html("Email content", sanitize_attributes=False)
    imported_statement = fields.Many2one("account.move")

    def _import_statement(self, fname, fbinary):
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
