from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ProjectIssueTC(TransactionCase):

    def setUp(self):
        super(ProjectIssueTC, self).setUp()

        self.project = self.env.ref('project.project_project_1')

        self.stage_pending = self.project.type_ids[0]
        self.stage_pending.name = u'Working on it [after-sale: pending]'
        self.stage_wait = self.project.type_ids[1]
        self.stage_wait.name = u'Wait [after-sale: waiting-customer]'
        self.stage_reminder = self.project.type_ids[2]
        self.stage_reminder.name = u'Remind email [after-sale: reminder-email]'
        self.stage_pending = self.project.type_ids[3]
        self.stage_pending.name = u'Solved [after-sale: end-ok]'

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
