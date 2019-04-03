from datetime import datetime, timedelta

import mock

from odoo.fields import DATETIME_FORMAT
from odoo.tests.common import at_install, post_install, TransactionCase

from odoo.addons.payment_slimpay.models.payment import SlimpayClient


class FakeDoc(dict):
    pass


def fake_action(method, func, *args, **kwargs):
    if method == 'POST' and func == 'ack-payment-issue':
        return {'executionStatus': 'processed'}
    elif method == 'GET' and func == 'get-mandates':
        return {'reference': 'mandate ref'}
    elif method == 'POST' and func == 'create-payins':
        return {'executionStatus': 'toprocess', 'state': 'accepted'}
    else:
        raise RuntimeError('Unexpected call to slimpay API action: '
                           'method=%r, func=%r, args=%r, kwargs=%r',
                           method, func, args, kwargs)


def fake_issue_doc(id='fake_issue', date='2019-03-28', amount='12.35',
                   currency='EUR', payment_ref=None, subscriber_ref=None):

    payment_url = 'https://api.slimpay.net/alps#get-payment'
    subscriber_url = 'https://api.slimpay.net/alps#get-subscriber'

    subscriber = FakeDoc(id='fake_subscriber', reference=subscriber_ref)
    payment = FakeDoc({'id': 'fake_payment', 'reference': payment_ref,
                       'label': 'dummy label',
                       subscriber_url: mock.Mock(url=subscriber)})
    return FakeDoc({'id': id, 'dateCreated': date + 'T00:00:00',
                    'rejectAmount': str(amount), 'currency': currency,
                    payment_url: mock.Mock(url=payment)})


@at_install(False)
@post_install(True)
class ProjectTC(TransactionCase):

    def setUp(self):
        patcher = mock.patch(
            'odoo.addons.payment_slimpay.models.slimpay_utils.get_client')
        patcher.start()
        super(ProjectTC, self).setUp()
        self.addCleanup(patcher.stop)

        self.env['account.journal'].create({
            'name': 'Sales',
            'code': 'INV',
            'company_id': self.env.user.company_id.id,
            'type': 'sale',
        })

        ref = self.env.ref

        self.project = ref('payment_slimpay_issue.project_payment_issue')

        customer_account = self.env['account.account'].create({
            'code': u'cust_acc', 'name': u'customer account',
            'user_type_id': ref('account.data_account_type_receivable').id,
            'reconcile': True,
        })

        customer_journal = self.env['account.journal'].create({
            'name': 'Customer journal',
            'code': 'RC',
            'company_id': self.env.user.company_id.id,
            'type': 'bank',
            'default_debit_account_id': customer_account.id,
            'default_credit_account_id': customer_account.id,
        })

        revenue_account = self.env['account.account'].create({
            'code': u'rev_acc', 'name': u'revenue account',
            'user_type_id': ref('account.data_account_type_revenue').id,
        })

        slimpay = self.env['payment.acquirer'].search(
            [('provider', '=', 'slimpay')], limit=1).ensure_one()
        self.partner = ref('base.res_partner_3')
        self.partner.update({
            'property_account_receivable_id': customer_account.id,
            'payment_token_ids': [(0, 0, {
                'name': 'Test Slimpay Token',
                'active': True, 'acquirer_id': slimpay.id,
                'acquirer_ref': 'Slimpay mandate ref',
            })],
        })

        self.invoice = self.env['account.invoice'].create({
            'name': u'Test Invoice',
            'reference_type': 'none',
            'payment_term_id': self.env.ref(
                'account.account_payment_term_advance').id,
            'journal_id': self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1).id,
            'partner_id': self.partner.id,
            'account_id': customer_account.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'product test 5',
                'product_id': ref('product.product_product_5').id,
                'account_id': revenue_account.id,
                'price_unit': 100.00,
            })],
        })
        self.invoice.action_invoice_open()

        Transaction = self.env['payment.transaction']
        self.transaction = Transaction.create({
            'reference': Transaction.get_next_reference(self.invoice.number),
            'acquirer_id': slimpay.id,
            'payment_token_id': self.partner.payment_token_ids[0].id,
            'amount': self.invoice.residual,
            'state': 'done',
            'date_validate': '2019-01-01',
            'currency_id': self.invoice.currency_id.id,
            'partner_id': self.partner.id,
            'partner_country_id': self.partner.country_id.id,
            'partner_city': self.partner.city,
            'partner_zip': self.partner.zip,
            'partner_email': self.partner.email,
            })

        payment = self.env['account.payment'].create({
            'company_id': self.env.user.company_id.id,
            'partner_id': self.invoice.partner_id.id,
            'partner_type': 'customer',
            'state': 'draft',
            'payment_type': 'inbound',
            'journal_id': customer_journal.id,
            'payment_method_id': ref(
                'payment.account_payment_method_electronic_in').id,
            'amount': self.invoice.amount_total,
            'payment_transaction_id': self.transaction.id,
            'invoice_ids': [(6, 0, [self.invoice.id])],
        })

        payment.post()

        self.assertEqual(self.invoice.state, 'paid')

        prod = self.env.ref('payment_slimpay_issue.rejected_sepa_fee_product')
        prod.property_account_income_id = revenue_account.id

    def _execute_cron(self, slimpay_issues):
        ProjectIssue = self.env['project.issue']

        with mock.patch.object(
                ProjectIssue, '_slimpay_payment_issue_fetch',
                return_value=slimpay_issues):
            with mock.patch.object(
                    SlimpayClient, 'action', side_effect=fake_action) as act:
                with mock.patch.object(
                        SlimpayClient, 'get', side_effect=lambda o: o) as get:
                    ProjectIssue._slimpay_payment_issue_cron()
        return act, get

    def _project_issues(self):
        return self.env['project.issue'].search([
            ('project_id', '=', self.project.id)
        ], order='invoice_unpaid_count')

    def assertStage(self, issue, ref_name):
        self.assertEqual(issue.stage_id.get_xml_id().values(),
                         ['payment_slimpay_issue.%s' % ref_name])

    def assertIssuesAck(self, act, *expected_slimpay_ids):
        issue_acks = self._action_calls(act, 'ack-payment-issue')
        self.assertEqual(set(kw['doc']['id'] for (args, kw) in issue_acks),
                         set(expected_slimpay_ids))

    def _action_calls(self, act, func_name):
        return [c for c in act.call_args_list if c[0][1] == func_name]

    def test_cron(self):

        # First payment issue:
        # - payment issue 1 cannot be attributed to an odoo
        #   transaction (the payment has no TR reference), so an odoo
        #   issue must be created in the orphan column
        # - payment issue 2 can be linked to an odoo transaction (see
        #   the payment reference), so an odoo issue must be created
        #   and linked to the corresponding invoice
        # - the issue must be put in the "warn partner and wait" stage

        act, get = self._execute_cron([
            fake_issue_doc(id='i1'),
            fake_issue_doc(id='i2',
                           payment_ref='TR%d' % self.transaction.id,
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

        self.assertStage(issue1, 'stage_orphan')
        self.assertStage(issue2, 'stage_warn_partner_and_wait')

        self.assertIssuesAck(act, 'i1', 'i2')

        # Second payment issue for the `self.invoice` invoice:
        # - the previously created odoo issue must be found and its
        #   unpaid invoice counter incremented
        # - the invoice must be added a line for payment issue fees
        # - a new payment trial must be issued

        act, get = self._execute_cron([
            fake_issue_doc(id='i3',
                           payment_ref='TR%d' % self.transaction.id,
                           subscriber_ref=self.partner.id),
        ])

        issues = self._project_issues()
        self.assertEqual(len(issues), 2)
        issue1, issue2 = issues

        self.assertEqual(issue1.invoice_unpaid_count, 0)
        self.assertEqual(issue2.invoice_unpaid_count, 2)

        self.assertStage(issue1, 'stage_orphan')
        self.assertStage(issue2, 'stage_warn_partner_and_wait')

        self.assertEqual(issue2.invoice_id.amount_total, 104.17)

        self.assertIssuesAck(act, 'i3')

        # Third payment issue for the `self.invoice` invoice:
        # - the previously created odoo issue must be found and its
        #   unpaid invoice counter incremented
        # - the invoice must be added a line for payment issue fees
        # - no new payment trial must be issued
        # - the issue must be moved to a "max trial number reach"
        #   column so that the risk team contacts the partner and
        #   handles the case manually

        act, get = self._execute_cron([
            fake_issue_doc(id='i4',
                           payment_ref='TR%d' % self.transaction.id,
                           subscriber_ref=self.partner.id),
        ])

        issues = self._project_issues()
        self.assertEqual(len(issues), 2)
        issue1, issue2 = issues

        self.assertEqual(issue1.invoice_unpaid_count, 0)
        self.assertEqual(issue2.invoice_unpaid_count, 3)

        self.assertStage(issue1, 'stage_orphan')
        self.assertStage(issue2, 'stage_max_trials_reached')

        self.assertEqual(issue2.invoice_id.amount_total, 108.34)

        self.assertIssuesAck(act, 'i4')

    def _reset_on_time_actions_last_run(self):
        for action in self.env['base.action.rule'].search([
                ('kind', '=', 'on_time')]):
            xml_ids = action.get_xml_id().values()
            if xml_ids and xml_ids[0].startswith('payment_slimpay_issue'):
                action.last_run = False

    def test_actions(self):
        issue = self.env['project.issue'].create({
            'project_id': self.project.id,
            'name': u'Test issue',
            'partner_id': self.partner.id,
            'invoice_id': self.invoice.id,
        })

        # Check a message is sent when entering the warn and wait stage
        issue.stage_id = self.env.ref(
            'payment_slimpay_issue.stage_warn_partner_and_wait').id,
        self.assertEqual(issue.message_ids[0:1].subject,
                         'YourCompany: rejected payment')

        # Check the issue moves to the payment retry stage 3 days after
        # and a payment is issued.
        move_date = datetime.utcnow() - timedelta(days=3, minutes=1)
        issue.date_last_stage_update = move_date.strftime(DATETIME_FORMAT)
        self._reset_on_time_actions_last_run()

        with mock.patch.object(
                SlimpayClient, 'action', side_effect=fake_action) as act:
            # triggers actions based on time
            self.env['base.action.rule']._check()

        new_payins = self._action_calls(act, 'create-payins')
        self.assertEqual(len(new_payins), 1)

        self.assertEqual(issue.stage_id, self.env.ref(
            'payment_slimpay_issue.stage_retry_payment_and_wait'))

        # Check the issue finally goes into fixed stage 8 days later
        move_date = datetime.utcnow() - timedelta(days=8, minutes=1)
        issue.date_last_stage_update = move_date.strftime(DATETIME_FORMAT)
        self._reset_on_time_actions_last_run()

        self.env['base.action.rule']._check()  # triggers actions based on time
        self.assertEqual(issue.stage_id, self.env.ref(
            'payment_slimpay_issue.stage_issue_fixed'))
