import os.path as osp
from datetime import date, timedelta
from urllib import parse

import requests_mock

from odoo import fields
from odoo.tests.common import SavepointCase
from odoo.tools.config import config

HERE = osp.abspath(osp.dirname(__file__))


class SlimpayStatementImportBaseTC(SavepointCase):
    "Base class for statement import tests"

    def create_statement_import(self):
        model = self.env["slimpay_statements_autoimport.statement_import"]

        # An html email arrives (mail alias behaviour not checked here)
        html = '<a href="http://example.com/my_report.csv">lien de téléchargement</a>'
        si = model.message_new({"subject": "test subject", "body": html})

        # Check the created import object:
        self.assertEqual(si.name, "test subject")
        self.assertEqual(si.mail_html, html)

        return si

    def _import_csv(self, fname, si=None):
        si = si or self.si

        with open(osp.join(HERE, fname)) as fobj:
            csv_content = fobj.read()

        with requests_mock.Mocker() as rm:
            rm.get("http://example.com/my_report.csv", text=csv_content)
            si.fetch_and_import_statement()


class SlimpayStatementImportTC(SlimpayStatementImportBaseTC):
    "Test the statement import behaviour"

    def setUp(self):
        "Simulate an incoming message and fetch the job for coming tests"
        super().setUp()

        self.si = self.create_statement_import()

        # Check a job was created and can be navigated to using the dedicated action:
        self.job = self.env["queue.job"].search([], limit=1, order="id desc")
        self.assertEqual(
            self.job.func_string,
            "%s(%d,).fetch_and_import_statement()" % (self.si._name, self.si.id),
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


class SlimpayStatementImportCronTC(SlimpayStatementImportBaseTC):
    def setUp(self):
        super().setUp()

        self.config_name = "slimpay_statements_autoimport"
        config.misc[self.config_name] = {
            "login": "my_login",
            "password": "my_password",
            "reports_url": "https://example.com/reports/",
        }

    def _run_reporting_cron(self, *arg):
        self.env["slimpay_statements_autoimport.statement_import"]._cron_reporting(*arg)

    def test_no_crash_without_config(self):
        "Cron should not crash when there is no dedicated config"
        config.misc.pop(self.config_name, None)
        self._run_reporting_cron()

    def test_no_suitable_start_date_error(self):
        "Cron should crash when no start date is given and there is no previous import"
        with self.assertRaises(ValueError) as err:
            self._run_reporting_cron()

        expected_msg = "Cannot determine a suitable slimpay import start date."
        self.assertEqual(err.exception.args, (expected_msg,))

    def test_no_suitable_start_date_nothing_done_1(self):
        "Cron should do nothing if import_only_older_days is negative"
        self.env["ir.config_parameter"].set_param(
            "slimpay_statements_autoimport.import_only_older_days",
            -1,
        )
        self._run_reporting_cron(date.today() - timedelta(days=30))

    def test_no_suitable_start_date_nothing_done_2(self):
        "Cron should do nothing if import_duration_days is negative or zero"
        self.env["ir.config_parameter"].set_param(
            "slimpay_statements_autoimport.import_duration_days",
            0,
        )
        self._run_reporting_cron(date.today() - timedelta(days=30))

    def test_no_suitable_start_date_nothing_done_3(self):
        "Cron should do nothing if start_date is not old enough"
        self._run_reporting_cron(date.today() - timedelta(days=4))

    def test_end_date_with_fiscal_year(self):
        model = self.env["slimpay_statements_autoimport.statement_import"]
        duration = model._get_int_param("import_duration_days", 0)

        report_date = date.today() - timedelta(days=30)

        fy = self.env["account.fiscal.year"].create(
            {
                "name": "test_fy",
                "date_from": report_date - timedelta(days=363),
                "date_to": report_date + timedelta(days=2),
            }
        )
        # Check test pre-requisites:
        self.assertTrue(fy.date_to >= report_date >= fy.date_from)
        self.assertTrue(report_date + timedelta(days=duration) > fy.date_to)

        date_from, date_to = model._compute_reporting_dates(report_date)
        self.assertEqual(date_to, fields.Date.to_string(fy.date_to))

    def test_ok_with_previous_import(self):
        si = self.create_statement_import()
        self._import_csv("reporting_sample.csv", si)

        with requests_mock.Mocker() as rm:
            rm.post(
                "https://api.preprod.slimpay.com/oauth/token",
                json={"access_token": "my_token"},
            )
            rm.post("https://example.com/reports/")
            self._run_reporting_cron()

        req1, req2 = rm.request_history

        req1_query = parse.parse_qs(req1.text)
        self.assertEqual(req1_query["username"], ["my_login"])
        self.assertEqual(req1_query["password"], ["my_password"])

        req2_json = req2.json()
        self.assertEqual(req2_json["startDate"], "2023-11-04")
        self.assertEqual(req2_json["endDate"], "2023-11-11")
        self.assertEqual(req2_json["locale"], "fr")
