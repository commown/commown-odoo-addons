from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ProjectIssueTC(TransactionCase):

    def _send_partner_email(self, issue):
        params = {
            'body': u'Test message',
            'message_type': u'comment',
            'subtype': 'mt_comment',
            'author_id': issue.partner_id.id,
        }
        return issue.message_post(**params)

    def test_last_partner_msg_date(self):
        issue = self.env.ref(
            'project_issue.crm_case_programnotgivingproperoutput0')
        self.assertEqual(issue.last_partner_msg_date, issue.create_date)
        msg = self._send_partner_email(issue)

        self.assertEqual(issue.last_partner_msg_date, msg.create_date)
        self.assertTrue(issue.last_partner_msg_date > issue.create_date)
