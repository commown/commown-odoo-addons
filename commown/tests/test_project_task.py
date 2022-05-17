from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ProjectTaskTC(TransactionCase):

    def setUp(self):
        super(ProjectTaskTC, self).setUp()

        self.project = self.env.ref(
            'commown_self_troubleshooting.support_project')

        # Adapt defined stages to our needs: use expected name
        # conventions and remove email model as they are buggy for
        # issues (their template model is task instead, which leads to
        # crashes)
        self.stage_pending = self.env["project.task.type"].create({
            'name': 'Working on it [after-sale: pending]',
            'mail_template_id': False})
        self.stage_pending.project_ids |= self.project
        self.stage_wait = self.stage_pending.copy({
            'name': 'Wait [after-sale: waiting-customer]',
            'mail_template_id': False})
        self.stage_reminder = self.stage_pending.copy({
            'name': 'Remind email [after-sale: reminder-email]',
            'mail_template_id': False})
        self.stage_end_ok = self.stage_pending.copy({
            'name': 'Solved [after-sale: end-ok]',
            'mail_template_id': False})
        self.stage_manual = self.stage_pending.copy({
            'name': 'Solved [after-sale: manual]',
            'mail_template_id': False})[0]

        self.partner = self.env.ref('base.partner_demo_portal')
        self.partner.update({'firstname': 'Flo', 'phone': '0000000000'})

        self.task = self.env['project.task'].create({
            'name': 'Commown test',
            'project_id': self.project.id,
            'stage_id': self.stage_pending.id,
            'partner_id': self.partner.id,
            'user_id': self.env.ref('base.user_demo').id,
        })

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
            "Commown : votre demande d'assistance se languit de vous !")
        self.assertEqual(message.author_id,
                         self.env.ref('base.user_demo').partner_id)

    def assertIsReminderSMS(self, message):
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertIn('ignorez ce SMS', message.body)

    def assertIsStageChangeMessage(self, message):
        self.assertEqual(message.subtype_id,
                         self.env.ref("project.mt_task_new"))

    def _test_send_reminders(self):
        """A reminder mail to followers and SMS to partner must be sent
        when task is put in the dedicated column.
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

    def _test_send_reminder_no_sms(self):
        """A reminder SMS must not be sent when a non-employee message
        (interpreted as a message from the partner) has already been sent.
        """

        # Check test prerequisite: task's partner is not an employee
        assert self.env.ref(
            'base.group_user') not in self.task.partner_id.mapped(
                'user_ids.groups_id')

        # Simulate partner sending a message, then put task back to reminder
        self._send_partner_email()
        message_num = len(self.task.message_ids)
        self.task.update({'stage_id': self.stage_reminder.id})

        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

    def _test_move_task_after_expiry(self):
        """ After 10 days spent in the reminder stage, crontab should
        automatically move the task into the 'end-ok' stage. """

        self.task.update({'stage_id': self.stage_reminder.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        self.env['base.automation']._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_end_ok)

    def _send_partner_email(self, author_id=None):
        self.env['mail.message'].create({
            'author_id': author_id or self.task.partner_id.id,
            'subject': 'Test subject',
            'body': "<p>Test body</p>",
            'message_type': 'comment',
            'model': 'project.task',
            'res_id': self.task.id,
            'subtype_id': self.env.ref('mail.mt_comment').id,
        })

    def test_move_task_when_message_arrives_if_not_from_employee(self):
        """ When a partner sends a message concerning an task, it moves
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

        other_partner.user_ids.groups_id -= self.env.ref("base.group_portal")
        other_partner.user_ids.groups_id |= employees
        self.task.update({'stage_id': self.stage_reminder.id})
        self._send_partner_email(author_id=other_partner.id)
        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_customer_long_waiting_task_to_reminder(self):

        self.task.update({'stage_id': self.stage_wait.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        self.env['base.automation']._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_long_waiting_manual_followup_to_pending(self):

        self.task.update({'stage_id': self.stage_manual.id})
        self.task.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.reset_actions_last_run()
        self.env['base.automation']._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_pending)

    def test_move_manual_long_waiting_task_when_message_arrives(self):
        """ When a customer message arrives which concerns a manually
        handled task, the task is moved to the pending stage. """

        self.task.update({'stage_id': self.stage_manual.id})

        self._send_partner_email()

        self.assertEqual(self.task.stage_id, self.stage_pending)

    def test_payment_task_process_automatically(self):
        inv = self.env['account.invoice'].search([]).filtered(
            lambda i: i.invoice_line_ids and not any(
                line.contract_line_id for line in i.invoice_line_ids))[0]
        self.task.invoice_id = inv.id
        iline = inv.invoice_line_ids[0]

        self.assertFalse(
            self.task.slimpay_payment_issue_process_automatically())

        contract = self.env['contract.contract'].create({
            'name': 'Test Contract',
            'partner_id': inv.partner_id.id,
            'contract_line_ids': [(0, 0, {
                "name": "line 1",
                "product_id": iline.product_id.id,
            })],
        })
        iline.contract_line_id = contract.contract_line_ids[0].id

        self.assertTrue(
            self.task.slimpay_payment_issue_process_automatically())
