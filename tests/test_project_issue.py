from datetime import datetime, timedelta

import mock

from odoo.fields import Date, DATETIME_FORMAT
from odoo.tests.common import at_install, post_install, TransactionCase

from odoo.addons.payment_slimpay.models.payment import SlimpayClient
from odoo.addons.queue_job.job import Job


class FakeDoc(dict):
    pass


def next_payment_reference(value=None, counter=[0]):
    if value is not None:
        counter[0] = value
    else:
        counter[0] = counter[0] + 1
    return 'slimpay_ref_%d' % counter[0]


def issue_emails(issue):
    return issue.message_ids.filtered(lambda m: m.message_type == 'email')


def fake_action(method, func, *args, **kwargs):
    if method == 'POST' and func == 'ack-payment-issue':
        return {'executionStatus': 'processed'}
    elif method == 'GET' and func == 'get-mandates':
        return {'reference': 'mandate ref'}
    elif method == 'POST' and func == 'create-payins':
        return {'executionStatus': 'toprocess', 'state': 'accepted',
                'reference': next_payment_reference()}
    else:
        raise RuntimeError('Unexpected call to slimpay API action: '
                           'method=%r, func=%r, args=%r, kwargs=%r',
                           method, func, args, kwargs)


def fake_action_crash_for(for_func, for_issue_id):
    def fake_action_crash(method, func, *args, **kwargs):
        if func == for_func and kwargs['doc']['id'] == for_issue_id:
            raise ValueError('ON PURPOSE TEST ERROR!')
        else:
            return fake_action(method, func, *args, **kwargs)
    return fake_action_crash


def fake_issue_doc(id='fake_issue', date='2019-03-28', amount='100.0',
                   currency='EUR', payment_ref=None, subscriber_ref=None,
                   **kwargs):

    payment_url = 'https://api.slimpay.net/alps#get-payment'
    subscriber_url = 'https://api.slimpay.net/alps#get-subscriber'

    subscriber = FakeDoc(id='fake_subscriber', reference=subscriber_ref)
    payment = FakeDoc({'id': 'fake_payment', 'reference': payment_ref,
                       'label': 'dummy label',
                       subscriber_url: mock.Mock(url=subscriber)})
    defaults = {'id': id, 'dateCreated': date + 'T00:00:00',
                'rejectAmount': str(amount), 'currency': currency,
                payment_url: mock.Mock(url=payment)}
    defaults.update(kwargs)
    return FakeDoc(defaults)


@at_install(False)
@post_install(True)
class ProjectTC(TransactionCase):

    def setUp(self):
        patcher = mock.patch(
            'odoo.addons.payment_slimpay.models.slimpay_utils.get_client')
        patcher.start()
        super(ProjectTC, self).setUp()
        self.addCleanup(patcher.stop)

        self.inv_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
        ]).ensure_one()
        # important for fees, see module doc:
        self.inv_journal.update_posted = True

        ref = self.env.ref

        self.project = ref('payment_slimpay_issue.project_payment_issue')

        self.customer_account = self.env['account.account'].create({
            'code': u'cust_acc', 'name': u'customer account',
            'user_type_id': ref('account.data_account_type_receivable').id,
            'reconcile': True,
        })

        self.customer_journal = self.env['account.journal'].create({
            'name': 'Customer journal',
            'code': 'RC',
            'company_id': self.env.user.company_id.id,
            'type': 'bank',
            'default_debit_account_id': self.customer_account.id,
            'default_credit_account_id': self.customer_account.id,
            'update_posted': True,
        })

        self.payment_mode = self.env['account.payment.mode'].create({
            'name': 'Electronic inbound to customer journal',
            'payment_method_id': ref(
                'payment.account_payment_method_electronic_in').id,
            'payment_type': 'inbound',
            'bank_account_link': 'fixed',
            'fixed_journal_id': self.customer_journal.id,
        })

        self.revenue_account = self.env['account.account'].create({
            'code': u'rev_acc', 'name': u'revenue account',
            'user_type_id': ref('account.data_account_type_revenue').id,
        })

        self.slimpay = self.env['payment.acquirer'].search(
            [('provider', '=', 'slimpay')], limit=1).ensure_one()
        self.partner = ref('base.res_partner_3')
        self.partner.update({
            'property_account_receivable_id': self.customer_account.id,
            'payment_token_ids': [(0, 0, {
                'name': 'Test Slimpay Token',
                'active': True, 'acquirer_id': self.slimpay.id,
                'acquirer_ref': 'Slimpay mandate ref',
            })],
        })

        tax = self.env['account.tax'].create({
            'name': 'my tax',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20.,
        })
        for _ref in ('management_fees_product', 'bank_fees_product'):
            prod = self.env.ref('payment_slimpay_issue.' + _ref)
            prod.property_account_income_id = self.revenue_account.id
            prod.taxes_id = [(6, 0, tax.ids)]

        # Reset payment reference between tests
        next_payment_reference(0)
        self.invoice, self.transaction, _p = self._create_inv_tx_and_payment()

        expenses_account = self.env['account.account'].create({
            'code': u'exp_acc', 'name': u'expenses account',
            'user_type_id': ref('account.data_account_type_expenses').id,
        })

        self.supplier_fees_product = self.env.ref(
            'payment_slimpay_issue.bank_supplier_fees_product')
        self.supplier_fees_product.update({
            'property_account_expense_id': expenses_account.id,
            'supplier_taxes_id': False,
        })

    def _execute_cron(self, slimpay_issues, action=None):
        ProjectIssue = self.env['project.issue']

        if action is None:
            action = fake_action
        with mock.patch.object(
                ProjectIssue, '_slimpay_payment_issue_fetch',
                return_value=slimpay_issues):
            with mock.patch.object(
                    SlimpayClient, 'action', side_effect=action) as act:
                with mock.patch.object(
                        SlimpayClient, 'get', side_effect=lambda o: o) as get:
                    ProjectIssue._slimpay_payment_issue_cron()
        return act, get

    def _project_issues(self):
        return self.env['project.issue'].search([
            ('project_id', '=', self.project.id)
        ], order='invoice_unpaid_count')

    def assertInStage(self, issue, ref_name):
        self.assertEqual(issue.stage_id.get_xml_id().values(),
                         ['payment_slimpay_issue.%s' % ref_name])

    def assertIssuesAcknowledged(self, act, *expected_slimpay_ids):
        issue_acks = self._action_calls(act, 'ack-payment-issue')
        self.assertEqual(set(kw['doc']['id'] for (args, kw) in issue_acks),
                         set(expected_slimpay_ids))

    def _action_calls(self, act, func_name):
        return [c for c in act.call_args_list if c[0][1] == func_name]

    def _create_odoo_issue(self, **kwargs):
        data = {
            'project_id': self.project.id,
            'name': u'Test issue',
            'partner_id': self.partner.id,
            'invoice_id': self.invoice.id,
        }
        data.update(kwargs)
        return self.env['project.issue'].create(data)

    def _create_inv_tx_and_payment(self):
        invoice = self.env['account.invoice'].create({
            'name': u'Test Invoice',
            'reference_type': 'none',
            'payment_term_id': self.env.ref(
                'account.account_payment_term_advance').id,
            'payment_mode_id': self.payment_mode.id,
            'journal_id': self.inv_journal.id,
            'partner_id': self.partner.id,
            'account_id': self.customer_account.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'product test 5',
                'product_id': self.env.ref('product.product_product_5').id,
                'account_id': self.revenue_account.id,
                'price_unit': 100.00,
            })],
        })
        invoice.action_invoice_open()

        Transaction = self.env['payment.transaction']
        transaction = Transaction.create({
            'reference': Transaction.get_next_reference(invoice.number),
            'acquirer_id': self.slimpay.id,
            'acquirer_reference': next_payment_reference(),
            'payment_token_id': self.partner.payment_token_ids[0].id,
            'amount': invoice.residual,
            'state': 'done',
            'date_validate': '2019-01-01',
            'currency_id': invoice.currency_id.id,
            'partner_id': self.partner.id,
            'partner_country_id': self.partner.country_id.id,
            'partner_city': self.partner.city,
            'partner_zip': self.partner.zip,
            'partner_email': self.partner.email,
            })

        payment = self.env['account.payment'].create({
            'company_id': self.env.user.company_id.id,
            'partner_id': invoice.partner_id.id,
            'partner_type': 'customer',
            'state': 'draft',
            'payment_type': 'inbound',
            'journal_id': self.customer_journal.id,
            'payment_method_id': self.env.ref(
                'payment.account_payment_method_electronic_in').id,
            'amount': invoice.amount_total,
            'payment_transaction_id': transaction.id,
            'invoice_ids': [(6, 0, [invoice.id])],
        })

        payment.post()

        self.assertEqual(invoice.state, 'paid')
        self.assertEqual(len(self._invoice_txs(invoice)), 1)

        return invoice, transaction, payment

    def _invoice_txs(self, invoice):
        return self.env['payment.transaction'].search([
            ('reference', 'like', invoice.number),
        ])

    def test_cron_first_issue(self):
        """ First payment issue:
        - payment issue 1 cannot be attributed to an odoo
          transaction (the payment has no tx reference), so an odoo
          issue must be created in the orphan column
        - payment issue 2 can be linked to an odoo transaction (see
          the payment reference), so an odoo issue must be created
          and linked to the corresponding invoice
        - the issue must be put in the "warn partner and wait" stage
        """

        act, get = self._execute_cron([
            fake_issue_doc(id='i1'),
            fake_issue_doc(id='i2',
                           payment_ref='slimpay_ref_1',
                           subscriber_ref=self.partner.id),
        ])

        issues = self._project_issues()
        self.assertEqual(len(issues), 2)

        issue1, issue2 = issues
        self.assertIn('Slimpay Id: i1', issue1.description)
        self.assertIn('Slimpay Id: i2', issue2.description)

        self.assertEqual(issue1.invoice_unpaid_count, 0)
        self.assertEqual(issue2.invoice_unpaid_count, 1)

        self.assertFalse(issue1.invoice_id)
        self.assertEqual(issue2.invoice_id, self.invoice)
        self.assertEqual(self.invoice.state, 'open')
        self.assertEqual(self.invoice.mapped('payment_ids.state'), ['draft'])

        self.assertInStage(issue1, 'stage_orphan')
        self.assertInStage(issue2, 'stage_warn_partner_and_wait')

        self.assertIssuesAcknowledged(act, 'i1', 'i2')

        self.assertIn('slimpay_ref_1 ', issue2.name)
        self.assertIn('2019-03-28', issue2.name)
        self.assertIn(issue2.invoice_id.number, issue2.name)

    def test_cron_second_issue(self):
        """ Second payment issue for the `self.invoice` invoice:
        - the previously created odoo issue must be found and its
          unpaid invoice counter incremented
        - the invoice must be added a line for payment issue fees
        - a new payment trial must be issued
        """

        issue = self._create_odoo_issue(invoice_unpaid_count=1)

        act, get = self._execute_cron([
            fake_issue_doc(id='i2',
                           payment_ref='slimpay_ref_1',
                           subscriber_ref=self.partner.id),
        ])

        self.assertEqual(len(self._project_issues()), 1)
        self.assertEqual(issue.invoice_unpaid_count, 2)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft'])
        self.assertInStage(issue, 'stage_warn_partner_and_wait')
        self.assertEqual(issue.invoice_id.amount_total, 105.)
        self.assertIssuesAcknowledged(act, 'i2')
        self.assertIn('slimpay_ref_1 ', issue.name)

    def test_cron_third_issue(self):
        """ Third payment issue for the `self.invoice` invoice:
        - the previously created odoo issue must be found and its
          unpaid invoice counter incremented
        - the invoice must be added a line for payment issue fees
        - no new payment trial must be issued
        - the issue must be moved to a "max trial number reach"
          column so that the risk team contacts the partner and
          handles the case manually
        """

        issue = self._create_odoo_issue(invoice_unpaid_count=2)

        act, get = self._execute_cron([
            fake_issue_doc(id='i3',
                           payment_ref='slimpay_ref_1',
                           subscriber_ref=self.partner.id),
        ])

        self.assertEqual(len(self._project_issues()), 1)
        self.assertEqual(issue.invoice_unpaid_count, 3)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft'])
        self.assertInStage(issue, 'stage_max_trials_reached')
        # We haven't simulated the previous invoice amount raise due
        # to 2nd payment issue here, so the invoice amount was
        # incremented with the fees amount only once:
        self.assertEqual(issue.invoice_id.amount_total, 105.)
        self.assertIssuesAcknowledged(act, 'i3')
        last_msg = issue.message_ids[0]
        self.assertEqual(last_msg.subject,
                         'YourCompany: max payment trials reached')

    def test_handle_focr(self):
        """An issue due to a creditor cancellation must be acknowledged to
        slimpay but should not create anything in the database.
        """

        act, get = self._execute_cron([
            fake_issue_doc(id='i1',
                           rejectReason='sepaReturnReasonCode.focr.reason'),
        ])

        self.assertEqual(len(self._project_issues()), 0)
        self.assertIssuesAcknowledged(act, 'i1')

    def _reset_on_time_actions_last_run(self):
        for action in self.env['base.action.rule'].search([
                ('kind', '=', 'on_time')]):
            xml_ids = action.get_xml_id().values()
            if xml_ids and xml_ids[0].startswith('payment_slimpay_issue'):
                action.last_run = False

    def _simulate_wait(self, issues, execute_jobs=True, **timedelta_kwargs):
        if execute_jobs:
            old_jobs = self.env["queue.job"].search([])
        target_date = datetime.utcnow() - timedelta(**timedelta_kwargs)
        for issue in issues:
            issue.date_last_stage_update = target_date.strftime(DATETIME_FORMAT)
            issue.invoice_next_payment_date = (
                Date.from_string(issue.invoice_next_payment_date)
                - timedelta(**timedelta_kwargs))
        self._reset_on_time_actions_last_run()
        with mock.patch.object(
                SlimpayClient, 'action', side_effect=fake_action) as act:
            # triggers actions based on time
            self.env['base.action.rule']._check()
            if execute_jobs:
                new_jobs = self.env["queue.job"].search([]) - old_jobs
                self.assertFalse(self._perform_jobs(new_jobs))
        return act

    def _perform_jobs(self, queued_jobs):
        """Execute given jobs in current test transaction and raised errors
        as a dict like {job resultset: exception}.

        Note the result is not the same as IRL as jobs do not use an individual
        transaction here but the same. Database savepoints are used to
        approximate reality though: successful jobs result is preserved, but
        erroneous jobs are rollbacked (while they would fail IRL).

        """
        errors = {}
        for queued_job in queued_jobs:
            job = Job.load(self.env, queued_job.uuid)
            # Save db state here as we are in a single transaction
            # which is not the case IRL where each job is executed
            # in its own.
            try:
                with self.env.cr.savepoint():
                    job.perform()
            except Exception as exc:
                errors[job.recordset] = exc
        return errors

    def test_actions(self):
        issue = self._create_odoo_issue()

        # Check a message is sent when entering the warn and wait stage
        issue.stage_id = self.env.ref(
            'payment_slimpay_issue.stage_warn_partner_and_wait').id
        last_msg = issue.message_ids[0]
        self.assertEqual(last_msg.subject, 'YourCompany: rejected payment')

        # 5 days later, issue must move to pay retry stage and a payin created

        # Prepare to new payment:
        self.invoice.payment_move_line_ids.remove_move_reconcile()

        act = self._simulate_wait(issue, days=6)
        self.assertInStage(issue, 'stage_retry_payment_and_wait')
        self.assertEqual(len(self._action_calls(act, 'create-payins')), 1)

        # Check the issue finally goes into fixed stage 8 days later
        self._simulate_wait(issue, days=8, minutes=1)
        self.assertInStage(issue, 'stage_issue_fixed')

    def _slimpay_supplier_invoices(self):
        slimpay_partner = self.env.ref(
                'payment_slimpay_issue.slimpay_fees_partner')
        return self.env['account.invoice'].search([
            ('partner_id', '=', slimpay_partner.id),
            ('type', '=', 'in_invoice'),
        ])

    def test_functional_1_trial_with_extra_bank_fees(self):

        fee_invoices_before = self._slimpay_supplier_invoices()

        act, get = self._execute_cron([
            fake_issue_doc(id='i1',
                           payment_ref='slimpay_ref_1',
                           subscriber_ref=self.partner.id,
                           amount=110),
        ])

        issue, = self._project_issues()
        self.assertIssuesAcknowledged(act, 'i1')
        self.assertEqual(issue.invoice_id, self.invoice)
        self.assertEqual(issue.invoice_unpaid_count, 1)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft'])
        self.assertEqual(issue.invoice_id.amount_total, 112)
        self.assertInStage(issue, 'stage_warn_partner_and_wait')
        last_msg = issue.message_ids[0]
        self.assertEqual(last_msg.subject, 'YourCompany: rejected payment')

        act = self._simulate_wait(issue, days=6)
        self.assertInStage(issue, 'stage_retry_payment_and_wait')
        self.assertEqual(len(self._action_calls(act, 'create-payins')), 1)

        act = self._simulate_wait(issue, days=8, minutes=1)
        self.assertInStage(issue, 'stage_issue_fixed')

        fee_invoices_after = self._slimpay_supplier_invoices()
        new_fee_invoices = fee_invoices_after - fee_invoices_before
        self.assertEqual(len(new_fee_invoices), 1)
        self.assertEqual(new_fee_invoices.amount_total, 10)
        self.assertEqual(new_fee_invoices.reference,
                         issue.invoice_id.number + '-REJ1')
        self.assertEqual(new_fee_invoices.mapped('invoice_line_ids.product_id'),
                         self.supplier_fees_product.product_variant_id)
        self.assertEqual(new_fee_invoices.state, 'open')

    def test_functional_3_trials(self):
        act, get = self._execute_cron([
            fake_issue_doc(id='i1',
                           payment_ref='slimpay_ref_1',
                           subscriber_ref=self.partner.id),
        ])

        issue = self._project_issues()

        self.assertEqual(len(issue), 1)
        self.assertIssuesAcknowledged(act, 'i1')
        self.assertEqual(issue.invoice_id, self.invoice)
        self.assertEqual(issue.invoice_unpaid_count, 1)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft'])
        self.assertEqual(issue.invoice_id.amount_total, 100.)
        self.assertInStage(issue, 'stage_warn_partner_and_wait')
        self.assertEqual(issue_emails(issue).mapped('subject'),
                         ['YourCompany: rejected payment'])
        self.assertEqual(self.invoice.state, 'open')

        act = self._simulate_wait(issue, days=6)
        self.assertInStage(issue, 'stage_retry_payment_and_wait')
        txs = self._invoice_txs(self.invoice)
        self.assertEqual(len(txs), 2)
        tx1, tx0 = txs
        self.assertEqual(tx0, self.transaction)
        payins = self._action_calls(act, 'create-payins')
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0][1]['params']['label'], 'dummy label')
        self.assertEqual(self.invoice.state, 'paid')
        self.assertEqual(len(issue_emails(issue)), 1)  # no new email
        self.assertIn('slimpay_ref_1 ', issue.name)

        act, get = self._execute_cron([
            fake_issue_doc(id='i2',
                           payment_ref='slimpay_ref_2',
                           subscriber_ref=self.partner.id),
        ])
        self.assertIssuesAcknowledged(act, 'i2')
        self.assertEqual(issue.invoice_unpaid_count, 2)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft', 'draft'])
        self.assertEqual(issue.invoice_id.amount_total, 105)
        self.assertInStage(issue, 'stage_warn_partner_and_wait')
        self.assertEqual(issue_emails(issue).mapped('subject'),
                         2 * ['YourCompany: rejected payment'])
        self.assertEqual(self.invoice.state, 'open')
        self.assertIn('slimpay_ref_2 - slimpay_ref_1 ',
                      issue.name)

        act = self._simulate_wait(issue, days=6)
        self.assertInStage(issue, 'stage_retry_payment_and_wait')
        txs = self._invoice_txs(self.invoice)
        self.assertEqual(len(txs), 3)
        self.assertEqual((txs[1], txs[2]), (tx1, tx0))
        tx2 = txs[0]
        payins = self._action_calls(act, 'create-payins')
        self.assertEqual(len(payins), 1)
        self.assertEqual(payins[0][1]['params']['label'], 'dummy label')
        self.assertEqual(self.invoice.state, 'paid')

        act, get = self._execute_cron([
            fake_issue_doc(id='i3',
                           payment_ref='slimpay_ref_3',
                           subscriber_ref=self.partner.id),
        ])
        self.assertIssuesAcknowledged(act, 'i3')
        self.assertEqual(issue.invoice_unpaid_count, 3)
        self.assertEqual(issue.invoice_id.mapped('payment_ids.state'),
                         ['draft', 'draft', 'draft'])
        self.assertEqual(issue.invoice_id.amount_total, 110)
        self.assertInStage(issue, 'stage_max_trials_reached')
        self.assertEqual(issue_emails(issue)[0].subject,
                         'YourCompany: max payment trials reached')
        self.assertFalse(self._action_calls(act, 'create-payins'))
        self.assertEqual(len(self._invoice_txs(self.invoice)), 3)
        self.assertIn('slimpay_ref_3 - slimpay_ref_2 - slimpay_ref_1 ',
                      issue.name)

    def test_db_savepoint(self):
        """ If only one http ack to Slimpay fails, its db updates and only
        them must be rolled back.
        """

        # Avoid confusion when debugging references: start at 1000
        next_payment_reference(999)

        # Create 3 invoice, transaction and payment series
        [(inv0, tx0, p0), (inv1, tx1, p1), (inv2, tx2, p2)] = [
            self._create_inv_tx_and_payment() for i in range(3)]

        # Execute test: generate 3 issues and simulate a crash when the
        # second is acknowledged to Slimpay
        act, get = self._execute_cron(
            [fake_issue_doc(id='i0',
                            payment_ref=tx0.acquirer_reference,
                            subscriber_ref=self.partner.id),
             fake_issue_doc(id='i1',
                            payment_ref=tx1.acquirer_reference,
                            subscriber_ref=self.partner.id),
             fake_issue_doc(id='i2',
                            payment_ref=tx2.acquirer_reference,
                            subscriber_ref=self.partner.id)
            ],
            fake_action_crash_for('ack-payment-issue', 'i1')
        )

        # Check the http ack method was called for all issue docs
        self.assertIssuesAcknowledged(act, 'i0', 'i1', 'i2')
        # Check only the 2 invoice, transaction, payment serie was
        # rolled backed, not the others:
        self.assertEqual((inv0.state, inv1.state, inv2.state),
                         ('open', 'paid', 'open'))
        self.assertEqual((p0.state, p1.state, p2.state),
                         ('draft', 'posted', 'draft'))

    def test_jobs_retry_payment(self):
        "Payment retrials are isolated: if one crashes other are not affected"
        # 1. Prepare test data
        [(inv0, tx0, p0), (inv1, tx1, p1), (inv2, tx2, p2)] = [
            self._create_inv_tx_and_payment() for i in range(3)]

        self._execute_cron(
            [fake_issue_doc(id='i0',
                            payment_ref=tx0.acquirer_reference,
                            subscriber_ref=self.partner.id),
             fake_issue_doc(id='i1',
                            payment_ref=tx1.acquirer_reference,
                            subscriber_ref=self.partner.id),
             fake_issue_doc(id='i2',
                            payment_ref=tx2.acquirer_reference,
                            subscriber_ref=self.partner.id)
            ]
        )

        issues = self._project_issues()
        for issue in issues:
            self.assertInStage(issue, 'stage_warn_partner_and_wait')

        # 2. Remove one payment_mode to generate a crash and launch simulation
        inv1.payment_mode_id = False
        old_jobs = self.env["queue.job"].search([])
        self._simulate_wait(issues, days=6, execute_jobs=False)
        new_jobs = self.env["queue.job"].search([]) - old_jobs
        with mock.patch.object(
                SlimpayClient, 'action', side_effect=fake_action):
            errors = self._perform_jobs(new_jobs)

        # 3. Check issue states and job errors
        for issue in issues:
            exception = errors.get(issue)
            if issue.invoice_id == inv1:
                self.assertInStage(issue, 'stage_warn_partner_and_wait')
                self.assertIn('IntegrityError', repr(exception))
                self.assertIn('journal_id', repr(exception))
            else:
                self.assertInStage(issue, 'stage_retry_payment_and_wait')
                self.assertIsNone(exception)
