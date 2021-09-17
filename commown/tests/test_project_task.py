from odoo.tests.common import TransactionCase, at_install, post_install

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC

from .common import MockedEmptySessionMixin


class ProjectTaskMixin(object):

    def setUp(self):
        super().setUp()

        def ref(extid):
            return self.env.ref(
                'commown_self_troubleshooting.%s' % extid)

        self.project = ref('support_project')

        # Adapt defined stages to our needs: use expected name
        # conventions and do not use mail template for now
        # (transition from 10.0: to be simplified in 12.0 where
        # issues do not exist anymore and mail template won't crash
        # if of the wrong -task- type...)

        def adapt(extid, name):
            stage = ref(extid)
            stage.name = name
            return stage

        self.stage_pending = adapt('stage_pending',
                                   'Working on it [after-sale: pending]')
        self.stage_wait = adapt('stage_received',
                                'Wait [after-sale: waiting-customer]')
        self.stage_reminder = adapt('stage_long_term_followup',
                                    'Remind email [after-sale: reminder-email]')
        self.stage_end_ok = adapt('stage_solved',
                                  'Solved [after-sale: end-ok]')
        self.stage_manual = self.stage_pending.copy({
            'name': 'Solved [after-sale: manual]'
        })[0]

        self.partner = self.env.ref('base.partner_demo_portal')
        self.partner.update({'firstname': 'Flo', 'phone': '0000000000'})

        self.task = self.env['project.task'].create({
            'name': 'Commown test',
            'project_id': self.project.id,
            'stage_id': self.stage_pending.id,
            'partner_id': self.partner.id,
            'user_id': self.env.ref('base.user_demo').id,
        })


@at_install(False)
@post_install(True)
class ProjectTaskTC(ProjectTaskMixin, TransactionCase):

    def reset_actions_last_run(self):
        " Unset all commown actions' last_run date "
        action_refs = self.env['ir.model.data'].search([
            ('module', '=', 'commown'),
            ('model', '=', 'base.automation')]).mapped('name')
        for ref in action_refs:
            self.env.ref('commown.%s' % ref).last_run = False

    def assertIsReminderEmail(self, message):
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertEqual(
            message.subject,
            u"Commown : votre demande d'assistance se languit de vous !")
        self.assertEqual(message.author_id,
                         self.env.ref('base.user_demo').partner_id)

    def assertIsReminderSMS(self, message):
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertIn('ignorez ce SMS', message.body)

    def assertIsStageChangeMessage(self, message):
        self.assertEqual(message.subtype_id,
                         self.env.ref("project.mt_task_new"))

    def test_send_reminders(self):
        """A reminder mail to followers and SMS to partner must be sent
        when issue is put in the dedicated column.
        """

        message_num = len(self.task.message_ids)
        self.task.update({'stage_id': self.stage_reminder.id})

        # Check email message
        # 3 expected messages: email, sms, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 3)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        sms = self.task.message_ids[1]
        self.assertIsReminderSMS(sms)
        self.assertEqual(sms.mapped('notification_ids.res_partner_id.email'),
                         ['mail2sms@envoyersmspro.com'])
        self.assertIsReminderEmail(self.task.message_ids[2])

    def test_send_reminder_no_sms(self):
        """A reminder SMS must not be sent when a non-employee message
        (interpreted as a message from the partner) has already been sent.
        """

        # Check test prerequisite: issue's partner is not an employee
        assert self.env.ref(
            'base.group_user') not in self.task.partner_id.mapped(
                'user_ids.groups_id')

        # Simulate partner sending a message, then put issue back to reminder
        self._send_partner_email()
        message_num = len(self.task.message_ids)
        self.task.update({'stage_id': self.stage_reminder.id})

        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

    def test_move_issue_after_expiry(self):
        """ After 10 days spent in the reminder stage, crontab should
        automatically move the issue into the 'end-ok' stage. """

        self.task.update({'stage_id': self.stage_reminder.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        self.env['base.automation']._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_end_ok)

    def _send_partner_email(self, author_id=None):
        self.env['mail.message'].create({
            'author_id': author_id or self.task.partner_id.id,
            'subject': 'Test subject',
            'body': u"<p>Test body</p>",
            'message_type': 'comment',
            'model': 'project.task',
            'res_id': self.task.id,
            'subtype_id': self.env.ref('mail.mt_comment').id,
        })

    def test_move_issue_when_message_arrives_if_not_from_employee(self):
        """ When a partner sends a message concerning an issue, it moves
        automatically to the pending stage, unless it is an employee.
        """
        employees = self.env.ref('base.group_user')

        # Check test prerequisite
        assert employees not in self.task.partner_id.mapped(
            'user_ids.groups_id')

        self.task.update({'stage_id': self.stage_reminder.id})
        self._send_partner_email()
        self.assertEqual(self.task.stage_id, self.stage_pending)

        other_partner = self.env.ref('base.partner_demo_portal')
        self.task.update({'stage_id': self.stage_reminder.id})
        self._send_partner_email(author_id=other_partner.id)
        self.assertEqual(self.task.stage_id, self.stage_pending)

        other_partner.user_ids.groups_id = employees
        self.task.update({'stage_id': self.stage_reminder.id})
        self._send_partner_email(author_id=other_partner.id)
        self.assertEqual(self.task.stage_id, self.stage_reminder)

        employee = employees.users[0]
        self.task.update({'stage_id': self.stage_reminder.id})
        self._send_partner_email(author_id=employee.id)
        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_customer_long_waiting_issue_to_reminder(self):

        self.task.update({'stage_id': self.stage_wait.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        self.env['base.automation']._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_long_waiting_manual_followup_to_pending(self):
        self.task.update({'stage_id': self.stage_manual.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        base_automation = self.env['base.automation']
        base_automation._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_pending)

    def test_move_manual_long_waiting_issue_when_message_arrives(self):
        """ When a customer message arrives which concerns a manually
        handled issue, the issue is moved to the pending stage. """

        self.task.update({'stage_id': self.stage_manual.id})

        self._send_partner_email()

        self.assertEqual(self.task.stage_id, self.stage_pending)


class PaymentIssueTaskTC(ProjectTaskMixin, MockedEmptySessionMixin,
                         RentalSaleOrderTC):

    def setUp(self):
        super().setUp()

        tax = self.get_default_tax()
        so1 = self.create_sale_order(tax=tax)
        so1.action_confirm()
        contract = so1.mapped('order_line.contract_id')[0]
        self.inv_from_contract = contract._recurring_create_invoice()[0]

        so2 = self.create_sale_order(tax=tax)
        so2.action_confirm()
        self.inv_no_contract = self.env['account.invoice'].browse(
            so2.action_invoice_create())

    def test_payment_issue_process_automatically(self):
        self.task.invoice_id = self.inv_no_contract.id
        self.assertFalse(
            self.task.slimpay_payment_issue_process_automatically())

        self.task.invoice_id = self.inv_from_contract.id
        self.assertTrue(
            self.task.slimpay_payment_issue_process_automatically())
