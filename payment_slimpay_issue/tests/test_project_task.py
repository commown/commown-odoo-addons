from datetime import datetime, timedelta

import mock

from odoo.tests.common import SavepointCase, at_install, post_install
from odoo.tools import mute_logger

from odoo.addons.account_payment_slimpay.models.payment import SlimpayClient
from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.queue_job.tests.common import trap_jobs


class FakeDoc(dict):
    pass


def next_payment_reference(value=None, counter=[0]):
    if value is not None:
        counter[0] = value
    else:
        counter[0] = counter[0] + 1
    return "slimpay_ref_%d" % counter[0]


def task_emails(task):
    return task.message_ids.filtered("partner_ids")


def fake_action(method, func, *args, **kwargs):
    if method == "POST" and func == "ack-payment-issue":
        return {"executionStatus": "processed"}
    elif method == "GET" and func == "get-mandates":
        return {"reference": "mandate ref"}
    elif method == "POST" and func == "create-payins":
        return {
            "executionStatus": "toprocess",
            "state": "accepted",
            "reference": next_payment_reference(),
        }
    else:
        raise RuntimeError(
            "Unexpected call to slimpay API action: "
            "method=%r, func=%r, args=%r, kwargs=%r",
            method,
            func,
            args,
            kwargs,
        )


def fake_action_crash_for(for_func, for_issue_id):
    def fake_action_crash(method, func, *args, **kwargs):
        if func == for_func and kwargs["doc"]["id"] == for_issue_id:
            raise ValueError("ON PURPOSE TEST ERROR!")
        else:
            return fake_action(method, func, *args, **kwargs)

    return fake_action_crash


def fake_issue_doc(
    id="fake_issue",
    date="2019-03-28",
    amount="100.0",
    currency="EUR",
    payment_ref=None,
    subscriber_ref=None,
    **kwargs
):

    payment_url = "https://api.slimpay.net/alps#get-payment"
    subscriber_url = "https://api.slimpay.net/alps#get-subscriber"

    subscriber = FakeDoc(id="fake_subscriber", reference=subscriber_ref)
    payment = FakeDoc(
        {
            "id": "fake_payment",
            "reference": payment_ref,
            "label": "dummy label",
            subscriber_url: mock.Mock(url=subscriber),
        }
    )
    defaults = {
        "id": id,
        "dateCreated": date + "T00:00:00",
        "rejectAmount": str(amount),
        "currency": currency,
        payment_url: mock.Mock(url=payment),
    }
    defaults.update(kwargs)
    return FakeDoc(defaults)


@at_install(False)
@post_install(True)
class ProjectTC(SavepointCase):
    def setUp(self):
        patcher = mock.patch(
            "odoo.addons.account_payment_slimpay" ".models.slimpay_utils.get_client"
        )
        patcher.start()
        super(ProjectTC, self).setUp()
        self.addCleanup(patcher.stop)

        self.inv_journal = (
            self.env["account.journal"]
            .search(
                [
                    ("type", "=", "sale"),
                ]
            )
            .ensure_one()
        )
        # important for fees, see module doc:
        self.inv_journal.update_posted = True

        ref = self.env.ref

        self.project = ref("payment_slimpay_issue.project_payment_issue")

        self.customer_account = self.env["account.account"].create(
            {
                "code": "cust_acc",
                "name": "customer account",
                "user_type_id": ref("account.data_account_type_receivable").id,
                "reconcile": True,
            }
        )

        self.customer_journal = self.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": self.env.user.company_id.id,
                "type": "bank",
                "update_posted": True,
            }
        )

        self.payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "Electronic inbound to customer journal",
                "payment_method_id": ref(
                    "payment.account_payment_method_electronic_in"
                ).id,
                "payment_type": "inbound",
                "bank_account_link": "fixed",
                "fixed_journal_id": self.customer_journal.id,
            }
        )

        self.revenue_account = self.env["account.account"].create(
            {
                "code": "rev_acc",
                "name": "revenue account",
                "user_type_id": ref("account.data_account_type_revenue").id,
            }
        )

        self.slimpay = (
            self.env["payment.acquirer"]
            .search([("provider", "=", "slimpay")], limit=1)
            .ensure_one()
        )
        self.partner = ref("base.res_partner_3")
        self.partner.update(
            {
                # Avoid SMS not sent warnings:
                "mobile": "+33612345678",
                "country_id": self.env.ref("base.fr").id,
                "property_account_receivable_id": self.customer_account.id,
                "payment_token_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Slimpay Token",
                            "active": True,
                            "acquirer_id": self.slimpay.id,
                            "acquirer_ref": "Slimpay mandate ref",
                        },
                    )
                ],
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
            prod.property_account_income_id = self.revenue_account.id
            prod.taxes_id = [(6, 0, tax.ids)]

        # Reset payment reference between tests
        next_payment_reference(0)
        self.invoice, self.transaction, _p = self._create_inv_tx_and_payment()

        expenses_account = self.env["account.account"].create(
            {
                "code": "exp_acc",
                "name": "expenses account",
                "user_type_id": ref("account.data_account_type_expenses").id,
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

    def _execute_cron(self, slimpay_issues, action=None):
        ProjectTask = self.env["project.task"]

        if action is None:
            action = fake_action
        with mock.patch.object(
            ProjectTask, "_slimpay_payment_issue_fetch", return_value=slimpay_issues
        ):
            with mock.patch.object(SlimpayClient, "action", side_effect=action) as act:
                with mock.patch.object(
                    SlimpayClient, "get", side_effect=lambda o: o
                ) as get:
                    ProjectTask._slimpay_payment_issue_cron()
        return act, get

    def _project_tasks(self):
        return self.env["project.task"].search(
            [("project_id", "=", self.project.id)], order="invoice_unpaid_count"
        )

    def assertInStage(self, task, ref_name):
        self.assertEqual(
            list(task.stage_id.get_xml_id().values()),
            ["payment_slimpay_issue.%s" % ref_name],
        )

    def assertIssuesAcknowledged(self, act, *expected_slimpay_ids):
        issue_acks = self._action_calls(act, "ack-payment-issue")
        self.assertEqual(
            {kw["doc"]["id"] for (args, kw) in issue_acks}, set(expected_slimpay_ids)
        )

    def _action_calls(self, act, func_name):
        return [c for c in act.call_args_list if c[0][1] == func_name]

    def _create_odoo_task(self, **kwargs):
        data = {
            "project_id": self.project.id,
            "name": "Test task",
            "partner_id": self.partner.id,
            "invoice_id": self.invoice.id,
        }
        data.update(kwargs)
        return self.env["project.task"].create(data)

    def _create_inv_tx_and_payment(self):
        invoice = self.env["account.invoice"].create(
            {
                "name": "Test Invoice",
                "payment_term_id": self.env.ref(
                    "account.account_payment_term_advance"
                ).id,
                "payment_mode_id": self.payment_mode.id,
                "journal_id": self.inv_journal.id,
                "partner_id": self.partner.id,
                "account_id": self.customer_account.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "product test 5",
                            "product_id": self.env.ref("product.product_product_5").id,
                            "account_id": self.revenue_account.id,
                            "price_unit": 100.00,
                        },
                    )
                ],
            }
        )
        invoice.action_invoice_open()

        Transaction = self.env["payment.transaction"]
        transaction = Transaction.create(
            {
                "acquirer_id": self.slimpay.id,
                "acquirer_reference": next_payment_reference(),
                "payment_token_id": self.partner.payment_token_ids[0].id,
                "amount": invoice.residual,
                "state": "done",
                "date": "2019-01-01",
                "currency_id": invoice.currency_id.id,
                "partner_id": self.partner.id,
                "partner_country_id": self.partner.country_id.id,
                "partner_city": self.partner.city,
                "partner_zip": self.partner.zip,
                "partner_email": self.partner.email,
                "invoice_ids": [(6, 0, invoice.ids)],
            }
        )

        payment = self.env["account.payment"].create(
            {
                "company_id": self.env.user.company_id.id,
                "partner_id": invoice.partner_id.id,
                "partner_type": "customer",
                "state": "draft",
                "payment_type": "inbound",
                "journal_id": self.customer_journal.id,
                "payment_method_id": self.env.ref(
                    "payment.account_payment_method_electronic_in"
                ).id,
                "amount": invoice.amount_total,
                "payment_transaction_id": transaction.id,
                "invoice_ids": [(6, 0, [invoice.id])],
            }
        )

        payment.post()

        self.assertEqual(invoice.state, "paid")
        self.assertEqual(len(self._invoice_txs(invoice)), 1)

        return invoice, transaction, payment

    def _invoice_txs(self, invoice):
        return self.env["payment.transaction"].search(
            [
                ("reference", "like", invoice.number),
            ]
        )

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

        act, get = self._execute_cron(
            [
                fake_issue_doc(id="i1"),
                fake_issue_doc(
                    id="i2", payment_ref="slimpay_ref_1", subscriber_ref=self.partner.id
                ),
            ]
        )

        tasks = self._project_tasks()
        self.assertEqual(len(tasks), 2)

        task1, task2 = tasks
        self.assertIn("Slimpay Id: i1", task1.description)
        self.assertIn("Slimpay Id: i2", task2.description)

        self.assertEqual(task1.invoice_unpaid_count, 0)
        self.assertEqual(task2.invoice_unpaid_count, 1)

        self.assertFalse(task1.invoice_id)
        self.assertEqual(task2.invoice_id, self.invoice)
        self.assertEqual(self.invoice.state, "open")
        self.assertEqual(self.invoice.mapped("payment_ids.state"), ["cancelled"])

        self.assertInStage(task1, "stage_orphan")
        self.assertInStage(task2, "stage_warn_partner_and_wait")

        self.assertIssuesAcknowledged(act, "i1", "i2")

        self.assertIn("slimpay_ref_1 ", task2.name)
        self.assertIn("2019-03-28", task2.name)
        self.assertIn(task2.invoice_id.number, task2.name)

    def test_cron_second_issue(self):
        """Second payment issue for the `self.invoice` invoice:
        - the previously created odoo task must be found and its
          unpaid invoice counter incremented
        - the invoice must be added a line for payment issue fees
        - a new payment trial must be issued
        """

        task = self._create_odoo_task(invoice_unpaid_count=1)

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i2", payment_ref="slimpay_ref_1", subscriber_ref=self.partner.id
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 1)
        self.assertEqual(task.invoice_unpaid_count, 2)
        self.assertEqual(task.invoice_id.mapped("payment_ids.state"), ["cancelled"])
        self.assertInStage(task, "stage_warn_partner_and_wait")
        self.assertEqual(task.invoice_id.amount_total, 105.0)
        self.assertIssuesAcknowledged(act, "i2")
        self.assertIn("slimpay_ref_1 ", task.name)

    def test_cron_third_issue(self):
        """Third payment issue for the `self.invoice` invoice:
        - the previously created odoo task must be found and its
          unpaid invoice counter incremented
        - the invoice must be added a line for payment issue fees
        - no new payment trial must be issued
        - the task must be moved to a "max trial number reach"
          column so that the risk team contacts the partner and
          handles the case manually
        """

        task = self._create_odoo_task(invoice_unpaid_count=2)

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i3", payment_ref="slimpay_ref_1", subscriber_ref=self.partner.id
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 1)
        self.assertEqual(task.invoice_unpaid_count, 3)
        self.assertEqual(task.invoice_id.mapped("payment_ids.state"), ["cancelled"])
        self.assertInStage(task, "stage_max_trials_reached")
        # We haven't simulated the previous invoice amount raise due
        # to 2nd payment issue here, so the invoice amount was
        # incremented with the fees amount only once:
        self.assertEqual(task.invoice_id.amount_total, 105.0)
        self.assertIssuesAcknowledged(act, "i3")
        last_msg = task.message_ids[0]
        self.assertEqual(last_msg.subject, "YourCompany: max payment trials reached")

    def test_handle_focr(self):
        """An issue due to a creditor cancellation must be acknowledged to
        slimpay but should not create anything in the database.
        """

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1", rejectReason="sepaReturnReasonCode.focr.reason"
                ),
            ]
        )

        self.assertEqual(len(self._project_tasks()), 0)
        self.assertIssuesAcknowledged(act, "i1")

    def _reset_on_time_actions_last_run(self):
        for action in self.env["base.automation"].search([("trigger", "=", "on_time")]):
            xml_ids = list(action.get_xml_id().values())
            if xml_ids and xml_ids[0].startswith("payment_slimpay_issue"):
                action.last_run = False

    def _simulate_wait(self, task, check_job_function=False, **timedelta_kwargs):
        task.date_last_stage_update = datetime.utcnow() - timedelta(**timedelta_kwargs)
        task.invoice_next_payment_date = task.invoice_next_payment_date - timedelta(
            **timedelta_kwargs
        )
        self._reset_on_time_actions_last_run()
        with mock.patch.object(SlimpayClient, "action", side_effect=fake_action) as act:
            with trap_jobs() as trap:
                # triggers actions based on time
                self.env["base.automation"]._check()
            if check_job_function:
                trap.assert_jobs_count(1, only=check_job_function)
                trap.perform_enqueued_jobs()
        return act

    def test_actions(self):
        task = self._create_odoo_task()

        # Check a message is sent when entering the warn and wait stage
        task.stage_id = self.env.ref(
            "payment_slimpay_issue.stage_warn_partner_and_wait"
        ).id
        last_msg = task.message_ids[0]
        self.assertEqual(last_msg.subject, "YourCompany: rejected payment")

        # 5 days later, task must move to pay retry stage and a payin created

        # Prepare to new payment:
        self.invoice.payment_move_line_ids.remove_move_reconcile()

        act = self._simulate_wait(
            task, days=6, check_job_function=task._slimpay_payment_issue_retry_payment
        )
        self.assertInStage(task, "stage_retry_payment_and_wait")
        self.assertEqual(len(self._action_calls(act, "create-payins")), 1)

        # Check the task finally goes into fixed stage 8 days later
        self._simulate_wait(task, days=8, minutes=1)
        self.assertInStage(task, "stage_issue_fixed")

    def _slimpay_supplier_invoices(self):
        slimpay_partner = self.env.ref("payment_slimpay_issue.slimpay_fees_partner")
        return self.env["account.invoice"].search(
            [
                ("partner_id", "=", slimpay_partner.id),
                ("type", "=", "in_invoice"),
            ]
        )

    def test_functional_1_trial_with_extra_bank_fees(self):

        fee_invoices_before = self._slimpay_supplier_invoices()

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i1",
                    payment_ref="slimpay_ref_1",
                    subscriber_ref=self.partner.id,
                    amount=110,
                ),
            ]
        )

        (task,) = self._project_tasks()
        self.assertIssuesAcknowledged(act, "i1")
        self.assertEqual(task.invoice_id, self.invoice)
        self.assertEqual(task.invoice_unpaid_count, 1)
        self.assertEqual(task.invoice_id.mapped("payment_ids.state"), ["cancelled"])
        self.assertEqual(task.invoice_id.amount_total, 112)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        last_msg = task.message_ids[0]
        self.assertEqual(last_msg.subject, "YourCompany: rejected payment")

        act = self._simulate_wait(
            task, days=6, check_job_function=task._slimpay_payment_issue_retry_payment
        )
        self.assertInStage(task, "stage_retry_payment_and_wait")
        self.assertEqual(len(self._action_calls(act, "create-payins")), 1)

        act = self._simulate_wait(task, days=8, minutes=1)
        self.assertInStage(task, "stage_issue_fixed")

        fee_invoices_after = self._slimpay_supplier_invoices()
        new_fee_invoices = fee_invoices_after - fee_invoices_before
        self.assertEqual(len(new_fee_invoices), 1)
        self.assertEqual(new_fee_invoices.amount_total, 10)
        self.assertEqual(new_fee_invoices.reference, task.invoice_id.number + "-REJ1")
        self.assertEqual(
            new_fee_invoices.mapped("invoice_line_ids.product_id"),
            self.supplier_fees_product.product_variant_id,
        )
        self.assertEqual(new_fee_invoices.state, "open")

    def test_functional_3_trials(self):
        fr = self.env.ref("base.fr")
        self.partner.update({"country_id": fr.id, "phone": "+33747397654"})
        with trap_jobs() as trap:
            act, get = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="slimpay_ref_1",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )

        task = self._project_tasks()
        # Check that a job is created with this function. The function is tesed in a
        # specific test
        trap.assert_jobs_count(1, only=task.message_post_send_sms_html)

        self.assertEqual(len(task), 1)
        self.assertIssuesAcknowledged(act, "i1")
        self.assertEqual(task.invoice_id, self.invoice)
        self.assertEqual(task.invoice_unpaid_count, 1)
        self.assertEqual(task.invoice_id.mapped("payment_ids.state"), ["cancelled"])
        self.assertEqual(task.invoice_id.amount_total, 100.0)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        # When CI runs, commown module is installed and sends a SMS too, so
        # we use assertIn and not assertEquals below:
        emails = task_emails(task)
        self.assertIn("YourCompany: rejected payment", emails.mapped("subject"))
        self.assertEqual(self.invoice.state, "open")

        act = self._simulate_wait(
            task, days=6, check_job_function=task._slimpay_payment_issue_retry_payment
        )
        self.assertInStage(task, "stage_retry_payment_and_wait")
        txs = self._invoice_txs(self.invoice)
        self.assertEqual(len(txs), 2)
        tx1, tx0 = txs
        self.assertEqual(tx0, self.transaction)
        payins = self._action_calls(act, "create-payins")
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0][1]["params"]["label"], "dummy label")
        self.assertEqual(self.invoice.state, "paid")
        self.assertEqual(len(task_emails(task)), len(emails))  # no new email
        self.assertIn("slimpay_ref_1 ", task.name)

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i2", payment_ref="slimpay_ref_2", subscriber_ref=self.partner.id
                ),
            ]
        )
        self.assertIssuesAcknowledged(act, "i2")
        self.assertEqual(task.invoice_unpaid_count, 2)
        self.assertEqual(
            task.invoice_id.mapped("payment_ids.state"), ["cancelled", "cancelled"]
        )
        self.assertEqual(task.invoice_id.amount_total, 105)
        self.assertInStage(task, "stage_warn_partner_and_wait")
        emails = task_emails(task)
        self.assertEqual(
            [s for s in emails.mapped("subject") if "rejected" in s],
            2 * ["YourCompany: rejected payment"],
        )
        self.assertEqual(self.invoice.state, "open")
        self.assertIn("slimpay_ref_2 - slimpay_ref_1 ", task.name)

        act = self._simulate_wait(
            task, days=6, check_job_function=task._slimpay_payment_issue_retry_payment
        )
        self.assertInStage(task, "stage_retry_payment_and_wait")
        txs = self._invoice_txs(self.invoice)
        self.assertEqual(len(txs), 3)
        self.assertEqual((txs[1], txs[2]), (tx1, tx0))
        payins = self._action_calls(act, "create-payins")
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0][1]["params"]["label"], "dummy label")
        self.assertEqual(self.invoice.state, "paid")

        act, get = self._execute_cron(
            [
                fake_issue_doc(
                    id="i3", payment_ref="slimpay_ref_3", subscriber_ref=self.partner.id
                ),
            ]
        )
        self.assertIssuesAcknowledged(act, "i3")
        self.assertEqual(task.invoice_unpaid_count, 3)
        self.assertEqual(
            task.invoice_id.mapped("payment_ids.state"),
            ["cancelled", "cancelled", "cancelled"],
        )
        self.assertEqual(task.invoice_id.amount_total, 110)
        self.assertInStage(task, "stage_max_trials_reached")
        self.assertEqual(
            task_emails(task)[0].subject, "YourCompany: max payment trials reached"
        )
        self.assertFalse(self._action_calls(act, "create-payins"))
        self.assertEqual(len(self._invoice_txs(self.invoice)), 3)
        self.assertIn("slimpay_ref_3 - slimpay_ref_2 - slimpay_ref_1 ", task.name)

    def test_warning_is_logged_if_partner_has_no_mobile(self):
        self.partner.update({"phone": "", "mobile": ""})
        with self.assertLogs(
            "odoo.addons.payment_slimpay_issue.models.project_task", level="WARNING"
        ) as cm:
            act, get = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="slimpay_ref_1",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )
        expected_message = (
            "WARNING:odoo.addons.payment_slimpay_issue.models.project_task:Could not send SMS to %s (id %s): no phone number found"
            % (self.partner.name, self.partner.id)
        )
        self.assertEqual(expected_message, cm.output[0])

    def test_sms_is_sent_when_partner_has_mobile(self):
        fr = self.env.ref("base.fr")
        self.partner.update({"country_id": fr.id, "mobile": "0637174433"})
        # Check that a job is created
        with trap_jobs() as trap:
            act, get = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i1",
                        payment_ref="slimpay_ref_1",
                        subscriber_ref=self.partner.id,
                    ),
                ]
            )

        task = self._project_tasks()
        trap.assert_jobs_count(1, only=task.message_post_send_sms_html)

        # Check that the job execute the function to send sms with the right argumetns
        template = self.env.ref("payment_slimpay_issue.smspro_payment_issue")

        country_code = self.partner.country_id.code
        partner_mobile = normalize_phone(
            self.partner.get_mobile_phone(),
            country_code,
        )
        with mock.patch(
            "odoo.addons.commown_res_partner_sms.models."
            "mail_thread.MailThread.message_post_send_sms_html"
        ) as post_message:
            trap.perform_enqueued_jobs()
            post_message.assert_called_once_with(
                template,
                task,
                numbers=[partner_mobile],
                log_error=True,
            )

    def test_db_savepoint(self):
        """If only one http ack to Slimpay fails, its db updates and only
        them must be rolled back.
        """

        # Avoid confusion when debugging references: start at 1000
        next_payment_reference(999)

        # Create 3 invoice, transaction and payment series
        [(inv0, tx0, p0), (inv1, tx1, p1), (inv2, tx2, p2)] = [
            self._create_inv_tx_and_payment() for i in range(3)
        ]

        # Execute test: generate 3 issues and simulate a crash when the
        # second is acknowledged to Slimpay
        with mute_logger("odoo.addons.payment_slimpay_issue.models.project_task"):
            act, get = self._execute_cron(
                [
                    fake_issue_doc(
                        id="i0",
                        payment_ref=tx0.acquirer_reference,
                        subscriber_ref=self.partner.id,
                    ),
                    fake_issue_doc(
                        id="i1",
                        payment_ref=tx1.acquirer_reference,
                        subscriber_ref=self.partner.id,
                    ),
                    fake_issue_doc(
                        id="i2",
                        payment_ref=tx2.acquirer_reference,
                        subscriber_ref=self.partner.id,
                    ),
                ],
                fake_action_crash_for("ack-payment-issue", "i1"),
            )

        # Check the http ack method was called for all issue docs
        self.assertIssuesAcknowledged(act, "i0", "i1", "i2")
        # Check only the 2 invoice, transaction, payment serie was
        # rolled backed, not the others:
        self.assertEqual((inv0.state, inv1.state, inv2.state), ("open", "paid", "open"))
        self.assertEqual(
            (p0.state, p1.state, p2.state), ("cancelled", "posted", "cancelled")
        )
