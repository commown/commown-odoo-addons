import os.path as osp
from datetime import date

import requests_mock

from odoo.tests.common import SavepointCase

HERE = osp.abspath(osp.dirname(__file__))


class SlimpayStatementImportTC(SavepointCase):
    "Test the statement import behaviour"

    def setUp(self):
        "Simulate an incoming message and fetch the job for coming tests"
        super().setUp()

        model = self.env["slimpay_statements_autoimport.statement_import"]

        # An html email arrives (mail alias behaviour not checked here)
        html = '<a href="http://example.com/my_report.csv">lien de téléchargement</a>'
        self.si = model.message_new({"subject": "test subject", "body": html})

        # Check the created import object:
        self.assertEqual(self.si.name, "test subject")
        self.assertEqual(self.si.mail_html, html)

        # Check a job was created and can be navigated to using the dedicated action:
        self.job = self.env["queue.job"].search([], limit=1, order="id desc")
        self.assertEqual(
            self.job.func_string,
            "%s(%d,).fetch_and_import_statement()" % (model._name, self.si.id),
        )

    def test_error_no_link_found(self):
        "A clear error must raise when no download link is found in the incoming email"

        self.si.mail_html = "<p>no link in-there</p>"

        with self.assertRaises(ValueError) as err:
            self.si.fetch_and_import_statement()

        expected_msg = "Cannot find one download URL in the email"
        self.assertEqual(err.exception.args, (expected_msg,))

    def test_error_cannot_fetch_report(self):
        "A clear error must raise when report cannot be fetched from the download URL"

        with self.assertRaises(ValueError) as err:
            with requests_mock.Mocker() as rm:
                rm.get(
                    "http://example.com/my_report.csv",
                    status_code=403,
                    reason="Unauthorized",
                    text="Test error",
                )
                self.si.fetch_and_import_statement()

        self.assertEqual(
            err.exception.args,
            ("403 Unauthorized\nResponse:\nTest error",),
        )

    def _import_csv(self, fname):
        with open(osp.join(HERE, fname)) as fobj:
            csv_content = fobj.read()

        with requests_mock.Mocker() as rm:
            rm.get("http://example.com/my_report.csv", text=csv_content)
            self.si.fetch_and_import_statement()

    def test_error_no_balance_in_report(self):
        "A clear error must raise when the end balance cannot be found in the report"

        with self.assertRaises(ValueError) as err:
            self._import_csv("reporting_sample_no_balance.csv")

        expected_msg = "Couldn't find end balance line in imported statement!"
        self.assertEqual(err.exception.args, (expected_msg,))

    def test_error_incorrect_balance(self):
        "A clear error must raise when report and odoo end balance do not match"

        with self.assertRaises(ValueError) as err:
            self._import_csv("reporting_sample_wrong_balance.csv")

        expected_msg = "Account balance do not match at end of import"
        self.assertTrue(err.exception.args[0].startswith(expected_msg))

    def test_button_open_job(self):
        "Open job button must open related import job"
        action = self.si.button_open_job()
        self.assertEqual(action["res_model"], self.job._name)
        self.assertEqual(action["res_id"], self.job.id)

    def test_no_error(self):
        "Whole import scenario with and without errors"

        self._import_csv("reporting_sample.csv")

        self.assertTrue(self.si.imported_statement)
        self.assertEqual(self.si.name, "my_report")

        move = self.si.imported_statement
        self.assertTrue(all(aml.date == aml.date_maturity for aml in move.line_ids))
        self.assertEqual(move.date, date(2023, 11, 3))
