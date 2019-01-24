from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ProjectIssueTC(TransactionCase):

    def setUp(self):
        super(ProjectIssueTC, self).setUp()

        self.project = self.env.ref('project.project_project_1')

        # Adapt defined stages to our needs: use expected name
        # conventions and remove email model as they are buggy for
        # issues (their template model is task instead, which leads to
        # crashes)
        self.stage_pending = self.project.type_ids[0]
        self.stage_pending.update({
            'name': u'Working on it [after-sale: pending]',
            'mail_template_id': False})
        self.stage_wait = self.project.type_ids[1]
        self.stage_wait.update({
            'name': u'Wait [after-sale: waiting-customer]',
            'mail_template_id': False})
        self.stage_reminder = self.project.type_ids[2]
        self.stage_reminder.update({
            'name': u'Remind email [after-sale: reminder-email]',
            'mail_template_id': False})
        self.stage_end_ok = self.project.type_ids[3]
        self.stage_end_ok.update({
            'name': u'Solved [after-sale: end-ok]',
            'mail_template_id': False})

        self.partner = self.env.ref('base.res_partner_1')
        self.partner.update({'firstname': 'Flo', 'lastname': 'Cay'})

        self.issue = self.env['project.issue'].create({
            'name': u'Commown test',
            'project_id': self.project.id,
            'stage_id': self.stage_pending.id,
            'partner_id': self.partner.id,
        })

    def test_send_reminder_email(self):
        """ A reminder message to followers must be created when issue is put
        in the dedicated column. """

        message_num = len(self.issue.message_ids)
        self.issue.update({'stage_id': self.stage_reminder.id})

        # Check messages: one for the stage change, one for the email
        self.assertEqual(len(self.issue.message_ids), message_num + 2)
        message = self.issue.message_ids[1]
        self.assertEqual(message.subtype_id.get_xml_id().values(),
                         [u'mail.mt_comment'])
        self.assertIn('Bonjour Flo', message.body)
        self.assertIn('Pas de nouvelles', message.body)

    def test_move_issue_after_expiry(self):
        """ After 10 days spent in the reminder stage, crontab should
        automatically move the issue into the 'end-ok' stage. """

        self.issue.update({'stage_id': self.stage_reminder.id})
        self.issue.update({'date_last_stage_update': '2019-01-01 00:00:00'})

        self.env['base.action.rule']._check()  # method called by crontab

        self.assertEqual(self.issue.stage_id, self.stage_end_ok)

    def _send_partner_email(self):
        self.env['mail.message'].create({
            'author_id': self.issue.partner_id.id,
            'subject': u'Test subject',
            'body': u"<p>Test body</p>",
            'message_type': u'comment',
            'model': u'project.issue',
            'res_id': self.issue.id,
            'subtype_id': self.env.ref('mail.mt_comment').id,
        })

    def test_move_issue_in_reminder_when_partner_message_arrives(self):
        """ When an issue is in the reminder stage and it's partner sends a
        message concerning it, the issue moves automatically to the
        pending stage. """

        self.issue.update({'stage_id': self.stage_reminder.id})

        self._send_partner_email()

        self.assertEqual(self.issue.stage_id, self.stage_pending)

    def test_move_customer_waiting_issue_when_message_arrives(self):
        """ When a customer message arrives which concerns a waiting
        issue, the issue is moved to the pending stage. """

        self.issue.update({'stage_id': self.stage_wait.id})

        self._send_partner_email()

        self.assertEqual(self.issue.stage_id, self.stage_pending)
