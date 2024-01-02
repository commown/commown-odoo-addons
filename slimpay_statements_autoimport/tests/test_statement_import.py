import os.path as osp
from datetime import date

import requests_mock

from odoo.tests.common import SavepointCase

HERE = osp.abspath(osp.dirname(__file__))


class SlimpayStatementImportTC(SavepointCase):
    "Test the statement import behaviour"

    def test_functional(self):
        "Whole import scenario with and without errors"

        model = self.env["slimpay_statements_autoimport.statement_import"]

        # An html email arrives (mail alias behaviour not checked here)
        html = '<a href="http://example.com/my_report.csv">lien de téléchargement</a>'
        si = model.message_new({"subject": "test subject", "body": html})

        # Check the created import object:
        self.assertEqual(si.name, "test subject")
        self.assertEqual(si.mail_html, html)

        # Check a job was created and can be navigated to using the dedicated action:
        new_job = self.env["queue.job"].search([], limit=1, order="id desc")
        self.assertEqual(
            new_job.func_string,
            "%s(%d,).fetch_and_import_statement()" % (model._name, si.id),
        )
        action = si.button_open_job()
        self.assertEqual(action["res_model"], new_job._name)
        self.assertEqual(action["res_id"], new_job.id)

        # Check error case: no link found in the incoming email
        old_html = si.mail_html
        with requests_mock.Mocker() as rm:
            with self.env.cr.savepoint():
                si.mail_html = "<p>no link in-there</p>"
                with self.assertRaises(ValueError) as err:
                    si.fetch_and_import_statement()
            self.assertEqual(
                err.exception.args, ("Cannot find one download URL in the email",)
            )
            si.mail_html = old_html

        # Check error case: cannot fetch given URL (with an unauthorized error here):
        with requests_mock.Mocker() as rm:
            rm.get(
                "http://example.com/my_report.csv",
                status_code=403,
                reason="Unauthorized",
                text="Test error",
            )
            with self.env.cr.savepoint():
                with self.assertRaises(ValueError) as err:
                    si.fetch_and_import_statement()
            self.assertEqual(
                err.exception.args,
                ("403 Unauthorized\nResponse:\nTest error",),
            )

        # Check the standard (no error) case:
        with open(osp.join(HERE, "reporting_sample.csv")) as fobj:
            csv_content = fobj.read()

        with requests_mock.Mocker() as rm:
            rm.get("http://example.com/my_report.csv", text=csv_content)
            si.fetch_and_import_statement()

        self.assertTrue(si.imported_statement)
        self.assertEqual(si.name, "my_report")

        # Check the data corrections performed at the end of the import
        move = si.imported_statement
        self.assertTrue(all(aml.date == aml.date_maturity for aml in move.line_ids))
        self.assertEqual(move.date, date(2023, 11, 3))
