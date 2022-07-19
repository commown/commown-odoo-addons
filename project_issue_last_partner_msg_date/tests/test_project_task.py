
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class ProjectTaskTC(TransactionCase):

    def _send_partner_email(self, task):
        params = {
            'body': 'Test message',
            'message_type': 'comment',
            'subtype': 'mt_comment',
            'author_id': task.partner_id.id,
        }
        return task.message_post(**params)

    def test_create(self):
        task = self.env.ref('project.project_task_1').copy()  # calls create
        self.assertEqual(task.last_partner_msg_date, task.create_date)

    def test_message_post(self):
        task = self.env.ref('project.project_task_1')
        msg = self._send_partner_email(task)

        self.assertEqual(task.last_partner_msg_date, msg.create_date)
        self.assertTrue(task.last_partner_msg_date > task.create_date)
