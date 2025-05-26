from contextlib import contextmanager
from datetime import datetime, timedelta

import mock
import requests
import requests_mock

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.queue_job.tests.common import trap_jobs


def task_emails(task):
    return task.message_ids.filtered("partner_ids")


def fake_issue_doc(
    date="2019-03-28",
    amount="100.0",
    currency="EUR",
    payment_ref=None,
    subscriber_ref=None,
    **kwargs
):

    kwargs.setdefault("id", "fake_issue")
    payment_url = "https://api.slimpay.net/alps#get-payment"
    subscriber_url = "https://api.slimpay.net/alps#get-subscriber"
    ack_url = "https://api.slimpay.net/alps#ack-payment-issue"

    subscriber = {"id": kwargs["id"] + "_subscriber", "reference": subscriber_ref}

    payment = {
        "id": kwargs["id"] + "_payment",
        "reference": payment_ref,
        "label": "dummy label",
        "_links": {subscriber_url: {"href": "/subscribers/" + subscriber["id"]}},
        "fake_subscriber": subscriber,
    }

    issue = {
        "dateCreated": date + "T00:00:00",
        "rejectAmount": str(amount),
        "currency": currency,
        "_links": {
            payment_url: {"href": "/payments/" + payment["id"]},
            ack_url: {"href": "/issues/ack/" + kwargs["id"]},
        },
        "fake_payment": payment,
    }
    issue.update(kwargs)
    return issue


@tagged("-at_install", "post_install")
class ProjectTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if not cls.env.company.chart_template_id:  # pragma: no cover
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)

    def setUp(self):
        super().setUp()

        self.inv_journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

        ref = self.env.ref

        self.project = ref("payment_slimpay_issue.project_payment_issue")

        electronic_in = self.env["account.payment.method"].create(
            {
                "name": "Electronic In",
                "code": "electronic",
                "payment_type": "inbound",
            }
        )

        self.customer_journal = self.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": self.env.company.id,
                "type": "bank",
            }
        )

        self.payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "Electronic inbound to customer journal",
                "payment_method_id": electronic_in.id,
                "payment_type": "inbound",
                "bank_account_link": "fixed",
                "fixed_journal_id": self.customer_journal.id,
            }
        )

        self.income_account = self.env["account.account"].create(
            {
                "code": "rev.acc",
                "name": "income account",
                "account_type": "income",
            }
        )

        self.slimpay = ref("account_payment_slimpay.payment_provider_slimpay")
        self.slimpay.state = "enabled"

        self.partner = ref("base.res_partner_3")
        token = self.env["payment.token"].create(
            {
                "payment_details": "Test Slimpay Token",
                "active": True,
                "provider_id": self.slimpay.id,
                "provider_ref": "Slimpay mandate ref",
                "partner_id": self.partner.id,
            },
        )
        self.partner.update(
            {
                # Avoid SMS not sent warnings:
                "mobile": "+33612345678",
                "country_id": self.env.ref("base.fr").id,
                "payment_token_id": token.id,
            }
        )

        tax = self.env["account.tax"].create(
            {
                "name": "my tax",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 20.0,
            }
        )
        for _ref in ("management_fees_product", "bank_fees_product"):
            prod = self.env.ref("payment_slimpay_issue." + _ref)
            prod.property_account_income_id = self.income_account.id
            prod.taxes_id = [(6, 0, tax.ids)]

        self.invoice, self.transaction, self.payment = self._create_inv_tx_and_payment()

        expenses_account = self.env["account.account"].create(
            {
                "code": "exp.acc",
                "name": "expenses account",
                "account_type": "expense",
            }
        )

        self.supplier_fees_product = self.env.ref(
            "payment_slimpay_issue.bank_supplier_fees_product"
        )
        self.supplier_fees_product.update(
            {
                "property_account_expense_id": expenses_account.id,
                "supplier_taxes_id": False,
            }
        )

    def _mock_slimpay_base(self, mocker):
        "Mock all necessary slimpay requests to get a client and a basic root doc"

        slimpay_url = self.slimpay.slimpay_api_url
        mocker.post(slimpay_url + "/oauth/token", json={"access_token": "mytoken"})
        mocker.get(
            slimpay_url + "/",
            json={
                "_links": {
                    "https://api.slimpay.net/alps#search-payment-issues": {
                        "href": "/search-payment-issues",
                    },
                    "https://api.slimpay.net/alps#get-mandates": {
                        "href": "/get-mandates",
                    },
                    "https://api.slimpay.net/alps#create-payins": {
                        "href": "/create-payins",
                    },
                },
            },
        )

    @contextmanager
    def mocked_slimpay_payment(self, token=None, payin_ref="SDD-EXE-0001"):
        token = token or self.partner.payment_token_id
        mandate = {"id": token.provider_ref, "reference": "SLMP0000"}

        payin = {
            "reference": payin_ref,
            "state": "accepted",
            "executionStatus": "toprocess",
        }

        slimpay_url = self.slimpay.slimpay_api_url
        mandate_url = slimpay_url + "/get-mandates?id=%s" % mandate["id"]

        with requests_mock.Mocker() as mocker:
            self._mock_slimpay_base(mocker)
            mocker.get(mandate_url, json=mandate)
            mocker.post(slimpay_url + "/create-payins", json=payin)
            yield mocker

    def _mock_slimpay_issues(self, mocker, issues):
        """Mock all necessary slimpay requests for handling given payment issues:

        - to get given issues when asking all payment issues
        - to get each issue payment and subscriber
        - to acknowledge given issues
        """

        slimpay_url = self.slimpay.slimpay_api_url

        for issue in issues:
            payment = issue.pop("fake_payment")
            subscriber = payment.pop("fake_subscriber")
            mocker.get(
                slimpay_url + "/payments/" + payment["id"],
                json=payment,
            )
            mocker.get(
                slimpay_url + "/subscribers/" + subscriber["id"],
                json=subscriber,
            )
            if issue.pop("fake_ack_error", None):
                ack_kw = {"exc": requests.exceptions.ConnectTimeout}
            else:
                ack_kw = {"json": {"executionStatus": "processed"}}
            mocker.post(slimpay_url + "/issues/ack/" + issue["id"], **ack_kw)

        mocker.get(
            slimpay_url + "/search-payment-issues",
            json={"_embedded": {"paymentIssues": issues}},
        )

    def _execute_cron(self, slimpay_issues):

        with requests_mock.Mocker() as mocker:
            self._mock_slimpay_base(mocker)
            self._mock_slimpay_issues(mocker, slimpay_issues)
            self.env["project.task"]._slimpay_payment_issue_cron()

        return mocker

    def _project_tasks(self):
        return self.env["project.task"].search(
            [("project_id", "=", self.project.id)], order="invoice_unpaid_count"
        )

    def assertInStage(self, task, ref_name):
        self.assertEqual(
            list(task.stage_id.get_external_id().values()),
            ["payment_slimpay_issue.%s" % ref_name],
        )

    def assertIssuesAcknowledged(self, mocker, *expected_slimpay_ids):
        acked_issues = tuple(
            req.url.rsplit("/", 1)[-1]
            for req in mocker.request_history
            if "/ack/" in req.url
        )
        self.assertEqual(acked_issues, expected_slimpay_ids)

    def _action_calls(self, mocker, path):
        return [req for req in mocker.request_history if path in req.url]

    def _create_odoo_task(self, **kwargs):
        data = {
            "project_id": self.project.id,
            "name": "Test task",
            "partner_id": self.partner.id,
            "invoice_id": self.invoice.id,
        }
        data.update(kwargs)
        return self.env["project.task"].create(data)

    def _create_inv_tx_and_payment(self, num=0):
        invoice = self.env["account.move"].create(
            {
                "journal_id": self.inv_journal.id,
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "payment_mode_id": self.payment_mode.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "product test 5",
                            "product_id": self.env.ref("product.product_product_5").id,
                            "account_id": self.income_account.id,
                            "price_unit": 100.00,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        token = self.partner.payment_token_ids[0]
        journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

        register_payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": journal.id, "payment_token_id": token.id})
        )

        with self.mocked_slimpay_payment(payin_ref="SDD-EXE-%04d" % num):
            payment = register_payment._create_payments()

        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertEqual(len(invoice.transaction_ids), 1)

        return invoice, invoice.transaction_ids, payment

    def test_slimpay_fetch_all_issue_pages(self):
        "Check that when there are several issue pages all are fetched at once"

        url = self.slimpay.slimpay_api_url + "/search-payment-issues?page=%s"
        fetch_func = self.env["project.task"]._slimpay_payment_issue_fetch

        issues_page0 = [fake_issue_doc(id="i%d" % i) for i in range(5)]
        issues_page1 = [fake_issue_doc(id="i%d" % i) for i in range(5, 10)]

        with requests_mock.Mocker() as mocker:
            self._mock_slimpay_base(mocker)
            client = self.slimpay.slimpay_client()

            doc1 = {"_embedded": {"paymentIssues": issues_page0}, "next": "nomatter"}
            doc2 = {"_embedded": {"paymentIssues": issues_page1}}
            mocker.get(url % "0", json=doc1)
            mocker.get(url % "1", json=doc2)

            issue_docs = list(fetch_func(client))

        self.assertEqual([d["id"] for d in issue_docs], ["i%d" % i for i in range(10)])

    def test_no_partner_found(self):
        "When the partner ref at Slimpay is wrong the task is created without a partner"
        self._execute_cron([fake_issue_doc(id="i1", subscriber_ref=-1)])
        tasks = self._project_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertFalse(tasks.partner_id)

    def test_cron_first_issue(self):
        """First payment issue:
        - payment issue 1 cannot be attributed to an odoo
          transaction (the payment has no tx reference), so an odoo
          task must be created in the orphan column
        - payment issue 2 can be linked to an odoo transaction (see
          the payment reference), so an odoo task must be created
          and linked to the corresponding invoice
        - the task must be put in the "warn partner and wait" stage
        """

        mocker = self._execute_cron(
            [
                fake_issue_doc(id="i1", subscriber_ref=self.partner.id),
                fake_issue_doc(
                    id="i2", payment_ref="SDD-EXE-0000", subscriber_ref=self.partner.id
                ),
            ]
        )

        tasks = self._project_tasks()
        self.assertEqual(len(tasks), 2)

        task1, task2 = tasks
        self.assertIn("Slimpay Id: i1", task1.description)
        self.assertIn("Slimpay Id: i2", task2.description)

        self.assertEqual(task1.partner_id, self.partner)
        self.assertEqual(task2.partner_id, self.partner)

        self.assertEqual(task1.invoice_unpaid_count, 0)
        self.assertEqual(task2.invoice_unpaid_count, 1)

        self.assertFalse(task1.invoice_id)
        self.assertEqual(task2.invoice_id, self.invoice)
        self.assertEqual(self.invoice.payment_state, "not_paid")
        self.assertEqual(self.payment.state, "cancel")

        self.assertInStage(task1, "stage_orphan")
        self.assertInStage(task2, "stage_warn_partner_and_wait")

        self.assertIssuesAcknowledged(mocker, "i1", "i2")

        self.assertIn("SDD-EXE-0000", task2.name)
        self.assertIn("2019-03-28", task2.name)
        self.assertIn(task2.invoice_id.name, task2.name)

    def test_cron_second_issue(self):
        """Second payment issue for the `self.invoice` invoice:
        - the previously created odoo task must be found and its
          unpaid invoice counter incremented
        - the invoice must be added a line for payment issue fees
        - a new payment trial must be issued
        """

        task = self._create_odoo_task(invoice_unpaid_count=1)

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i2", payment_ref="SDD-EXE-0000", subscriber_ref=self.partner.id
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 1)
        self.assertEqual(task.invoice_unpaid_count, 2)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertInStage(task, "stage_warn_partner_and_wait")
        self.assertEqual(task.invoice_id.amount_total, 105.0)
        self.assertIssuesAcknowledged(mocker, "i2")
        self.assertIn("SDD-EXE-0000 ", task.name)

    def test_cron_third_issue(self):
        """Third payment issue for the `self.invoice` invoice:

        - the previously created odoo task must be found and its
          unpaid invoice counter incremented

        - We remove the bank fees product in this test to check it
          does not crash and the fees are not invoices

        - no new payment trial must be issued

        - the task must be moved to a "max trial number reach" column
          so that the risk team contacts the partner and handles the
          case manually

        """

        task = self._create_odoo_task(invoice_unpaid_count=2)

        self.env.ref("payment_slimpay_issue.management_fees_product").unlink()

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i3", payment_ref="SDD-EXE-0000", subscriber_ref=self.partner.id
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 1)
        self.assertEqual(task.invoice_unpaid_count, 3)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertInStage(task, "stage_max_trials_reached")
        # No management fees here! (the management product was removed)
        self.assertEqual(task.invoice_id.amount_total, 100.0)
        self.assertIssuesAcknowledged(mocker, "i3")
        last_msg = task.message_ids[0]
        self.assertIn("max payment trials reached", last_msg.subject)

    def test_handle_focr(self):
        """An issue due to a creditor cancellation must be acknowledged to
        slimpay but should not create anything in the database.
        """

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1", rejectReason="sepaReturnReasonCode.focr.reason"
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 0)
        self.assertIssuesAcknowledged(mocker, "i1")

    def test_reason_message(self):
        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1",
                    rejectReason="Insufficient funds",
                    returnReasonCode="AM04",
                )
            ]
        )

        tasks = self._project_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertIn(
            "Reject reason is AM04: Insufficient funds",
            "\n".join(tasks.mapped("message_ids.body")),
        )
        self.assertIssuesAcknowledged(mocker, "i1")

    def test_unknown_reason(self):
        "The unknown reason must be posted in a message but the issue handled normally"
        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1",
                    rejectReason="my unknown reason",
                    returnReasonCode="DUMMY-CODE",
                )
            ]
        )

        tasks = self._project_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertIn(
            "Reject reason is DUMMY-CODE: Unknown reject error: my unknown reason",
            "\n".join(tasks.mapped("message_ids.body")),
        )
        self.assertIssuesAcknowledged(mocker, "i1")

    def _reset_on_time_actions_last_run(self):
        for action in self.env["base.automation"].search([("trigger", "=", "on_time")]):
            xml_ids = list(action.get_external_id().values())
            if xml_ids and xml_ids[0].startswith(
                "payment_slimpay_issue"
            ):  # pragma: no cover
                action.last_run = False

    def _simulate_wait(self, task, check_job_function=False, **timedelta_kwargs):
        task.date_last_stage_update = datetime.utcnow() - timedelta(**timedelta_kwargs)
        task.invoice_next_payment_date = task.invoice_next_payment_date - timedelta(
            **timedelta_kwargs
        )
        self._reset_on_time_actions_last_run()
        with trap_jobs() as trap:
            # triggers actions based on time
            self.env["base.automation"]._check()
        if check_job_function:
            trap.assert_jobs_count(1, only=check_job_function)
            trap.perform_enqueued_jobs()

    def flush_tracking(self):
        """Force the creation of tracking values."""
        self.env.flush_all()
        self.cr.precommit.run()

    def test_actions(self):
        ref = self.env.ref
        task = self._create_odoo_task()
        self.flush_tracking()  # Be sure a tracking discard will not impact next flush

        # Check a message is sent when entering the warn and wait stage
        task.stage_id = ref("payment_slimpay_issue.stage_warn_partner_and_wait").id
        self.flush_tracking()
        last_msg = task.message_ids[0]
        self.assertIn("rejected payment", last_msg.subject)

        # 5 days later, task must move to pay retry stage and a payin created

        # Prepare to new payment:
        self.invoice.line_ids.remove_move_reconcile()

        job_func = task._slimpay_payment_issue_retry_payment
        with self.mocked_slimpay_payment() as mocker:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        self.assertInStage(task, "stage_retry_payment_and_wait")
        self.assertEqual(len(self._action_calls(mocker, "create-payins")), 1)

        # Check the task finally goes into fixed stage 8 days later
        self._simulate_wait(task, days=8, minutes=1)
        self.assertInStage(task, "stage_issue_fixed")

    def _prepare_retry_payment(self):
        ref = self.env.ref
        task = self._create_odoo_task()
        task.stage_id = ref("payment_slimpay_issue.stage_warn_partner_and_wait").id
        self.invoice.line_ids.remove_move_reconcile()
        return task

    def test_retry_payment_fallback_to_partner_token(self):
        "When retrying payment partner's token is used if last tx token cannot be used"
        task = self._prepare_retry_payment()

        # Now remove the past transactions (last transaction token is otherwise reused)
        # and partner's token, then launch the payment retry:
        task.invoice_id.transaction_ids.unlink()

        job_func = task._slimpay_payment_issue_retry_payment
        with self.mocked_slimpay_payment() as mocker:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        self.assertEqual(len(self._action_calls(mocker, "create-payins")), 1)

    def test_retry_payment_error_no_tx_nor_partner_token(self):
        "An exception is raised when no suitable token is found to retry payment"
        task = self._prepare_retry_payment()

        # Now remove the past transactions (last transaction token is otherwise reused)
        # and partner's token, then launch the payment retry:
        task.invoice_id.transaction_ids.unlink()
        task.invoice_id.partner_id.payment_token_id = False

        job_func = task._slimpay_payment_issue_retry_payment
        with self.assertRaises(UserError) as err:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        # Check the expected exception is raised:
        self.assertIn("could not find a payment token!", err.exception.args[0])

    def _slimpay_supplier_invoices(self):
        slimpay_partner = self.env.ref("payment_slimpay_issue.slimpay_fees_partner")
        return self.env["account.move"].search(
            [
                ("partner_id", "=", slimpay_partner.id),
                ("move_type", "=", "in_invoice"),
            ]
        )

    def test_functional_1_trial_with_extra_bank_fees(self):

        fee_invoices_before = self._slimpay_supplier_invoices()

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1",
                    payment_ref="SDD-EXE-0000",
                    subscriber_ref=self.partner.id,
                    amount=110,
                ),
            ]
        )

        (task,) = self._project_tasks()
        self.assertIssuesAcknowledged(mocker, "i1")
        self.assertEqual(task.invoice_id, self.invoice)
        self.assertEqual(task.invoice_unpaid_count, 1)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertEqual(task.invoice_id.amount_total, 112)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        last_msg = task.message_ids[0]
        self.assertIn("rejected payment", last_msg.subject)

        job_func = task._slimpay_payment_issue_retry_payment
        with self.mocked_slimpay_payment() as mocker:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        self.assertInStage(task, "stage_retry_payment_and_wait")
        self.assertEqual(len(self._action_calls(mocker, "create-payins")), 1)

        self._simulate_wait(task, days=8, minutes=1)
        self.assertInStage(task, "stage_issue_fixed")

        fee_invoices_after = self._slimpay_supplier_invoices()
        new_fee_invoices = fee_invoices_after - fee_invoices_before
        self.assertEqual(len(new_fee_invoices), 1)
        self.assertEqual(new_fee_invoices.amount_total, 10)
        self.assertEqual(new_fee_invoices.ref, task.invoice_id.name + "-REJ1")
        self.assertEqual(
            new_fee_invoices.mapped("invoice_line_ids.product_id"),
            self.supplier_fees_product.product_variant_id,
        )
        self.assertEqual(new_fee_invoices.payment_state, "not_paid")

    def test_without_bank_fees_product(self):
        """When the bank fees product is not present, no crash occurs...

        ...and no fees invoice is emitted
        """
        self.env.ref("payment_slimpay_issue.bank_supplier_fees_product").unlink()

        fee_invoices_before = self._slimpay_supplier_invoices()
        self._execute_cron(
            [
                fake_issue_doc(
                    id="i1",
                    payment_ref="SDD-EXE-0000",
                    subscriber_ref=self.partner.id,
                    amount=110,
                ),
            ]
        )
        self.assertEqual(self._slimpay_supplier_invoices(), fee_invoices_before)

    def test_functional_3_trials(self):
        fr = self.env.ref("base.fr")
        self.partner.update({"country_id": fr.id, "phone": "+33747397654"})
        with trap_jobs() as trap:
            mocker = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="SDD-EXE-0000",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )

        task = self._project_tasks()

        # Check that a job is created with this function.
        # The function itself is tested in a specific test.
        trap.assert_jobs_count(1, only=task.send_sms_from_template)

        self.assertEqual(len(task), 1)
        self.assertIssuesAcknowledged(mocker, "i1")
        self.assertEqual(task.invoice_id, self.invoice)
        self.assertEqual(task.invoice_unpaid_count, 1)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertEqual(task.invoice_id.amount_total, 100.0)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        # When CI runs, commown module is installed and sends a SMS too, so
        # we use assertIn and not assertEquals below:
        emails = task_emails(task)
        self.assertIn(
            "%s: rejected payment" % self.env.company.name, emails.mapped("subject")
        )
        self.assertEqual(self.invoice.payment_state, "not_paid")

        job_func = task._slimpay_payment_issue_retry_payment
        with self.mocked_slimpay_payment() as mocker:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        self.assertInStage(task, "stage_retry_payment_and_wait")
        txs = self.invoice.transaction_ids
        self.assertEqual(len(txs), 2)
        tx0, tx1 = txs.sorted("id")
        self.assertEqual(tx0, self.transaction)
        payins = self._action_calls(mocker, "create-payins")
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0].json()["label"], "dummy label")
        self.assertEqual(self.invoice.payment_state, "paid")
        self.assertEqual(len(task_emails(task)), len(emails))  # no new email
        self.assertIn("SDD-EXE-0000 ", task.name)

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i2", payment_ref="SDD-EXE-0001", subscriber_ref=self.partner.id
                ),
            ]
        )
        self.assertIssuesAcknowledged(mocker, "i2")
        self.assertEqual(task.invoice_unpaid_count, 2)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertEqual(task.invoice_id.amount_total, 105)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        emails = task_emails(task)
        self.assertEqual(
            [s for s in emails.mapped("subject") if "rejected" in s],
            2 * ["%s: rejected payment" % self.env.company.name],
        )
        self.assertEqual(self.invoice.payment_state, "not_paid")
        self.assertIn("SDD-EXE-0001 - SDD-EXE-0000 ", task.name)

        job_func = task._slimpay_payment_issue_retry_payment
        with self.mocked_slimpay_payment(payin_ref="SDD-EXE-0002") as mocker:
            self._simulate_wait(task, days=6, check_job_function=job_func)

        self.assertInStage(task, "stage_retry_payment_and_wait")
        txs = self.invoice.transaction_ids
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs.sorted("id")[:2], (tx0 | tx1))
        payins = self._action_calls(mocker, "create-payins")
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0].json()["label"], "dummy label")
        self.assertEqual(self.invoice.payment_state, "paid")

        mocker = self._execute_cron(
            [
                fake_issue_doc(
                    id="i3", payment_ref="SDD-EXE-0002", subscriber_ref=self.partner.id
                ),
            ]
        )
        self.assertIssuesAcknowledged(mocker, "i3")
        self.assertEqual(task.invoice_unpaid_count, 3)
        self.assertEqual(task.invoice_id.payment_state, "not_paid")
        self.assertEqual(task.invoice_id.amount_total, 110)
        self.assertInStage(task, "stage_max_trials_reached")
        self.assertEqual(
            task_emails(task)[0].subject,
            "%s: max payment trials reached" % self.env.company.name,
        )
        self.assertFalse(self._action_calls(mocker, "create-payins"))
        self.assertEqual(len(self.invoice.transaction_ids), 3)
        self.assertIn("SDD-EXE-0002 - SDD-EXE-0001 - SDD-EXE-0000 ", task.name)

    def test_warning_is_logged_if_partner_has_no_mobile(self):
        self.partner.update({"phone": "", "mobile": ""})
        with self.assertLogs(
            "odoo.addons.payment_slimpay_issue.models.project_task", level="WARNING"
        ) as cm:
            self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="SDD-EXE-0000",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )
        expected_message = (
            "WARNING:odoo.addons.payment_slimpay_issue.models.project_task:"
            "Could not send SMS to %s (id %s): no phone number found"
            % (self.partner.name, self.partner.id)
        )
        self.assertEqual(expected_message, cm.output[0])

    def test_sms_is_sent_when_partner_has_mobile(self):
        fr = self.env.ref("base.fr")
        self.partner.update({"country_id": fr.id, "mobile": "0637174433"})
        # Check that a job is created
        with trap_jobs() as trap:
            self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="SDD-EXE-0000",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )

        task = self._project_tasks()
        trap.assert_jobs_count(1, only=task.send_sms_from_template)

        # Check that the job execute the function to send sms with the right argumetns
        template = self.env.ref("payment_slimpay_issue.sms")

        country_code = self.partner.country_id.code
        partner_mobile = normalize_phone(
            self.partner.get_mobile_phone(),
            country_code,
        )
        with mock.patch(
            "odoo.addons.commown_res_partner_sms.models."
            "mail_thread.MailThread.send_sms_from_template"
        ) as post_message:
            trap.perform_enqueued_jobs()
            post_message.assert_called_once_with(
                template,
                task,
                sms_numbers=[partner_mobile],
            )

    def test_db_savepoint(self):
        """If only one http ack to Slimpay fails, its db updates and only
        them must be rolled back.
        """

        # Create 3 invoice, transaction and payment series
        [(inv0, tx0, p0), (inv1, tx1, p1), (inv2, tx2, p2)] = [
            self._create_inv_tx_and_payment(i + 1) for i in range(3)
        ]

        # Check test pre-requisites:
        self.assertEqual(
            (inv0.payment_state, inv1.payment_state, inv2.payment_state),
            ("paid", "paid", "paid"),
        )
        self.assertEqual((p0.state, p1.state, p2.state), ("posted", "posted", "posted"))

        # Execute test: generate 3 issues and simulate a crash when the
        # second is acknowledged to Slimpay
        with mute_logger("odoo.addons.payment_slimpay_issue.models.project_task"):
            mocker = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i0",
                        payment_ref=tx0.provider_reference,
                        subscriber_ref=self.partner.id,
                    ),
                    fake_issue_doc(
                        id="i1",
                        payment_ref=tx1.provider_reference,
                        subscriber_ref=self.partner.id,
                        fake_ack_error=True,
                    ),
                    fake_issue_doc(
                        id="i2",
                        payment_ref=tx2.provider_reference,
                        subscriber_ref=self.partner.id,
                    ),
                ],
            )

        # Check the http ack method was called for all issue docs
        self.assertIssuesAcknowledged(mocker, "i0", "i1", "i2")
        # Check only the 2 invoices, transactions, payments serie was
        # rolled backed, not the others:
        self.assertEqual(
            (inv0.payment_state, inv1.payment_state, inv2.payment_state),
            ("not_paid", "paid", "not_paid"),
        )
        self.assertEqual((p0.state, p1.state, p2.state), ("cancel", "posted", "cancel"))
