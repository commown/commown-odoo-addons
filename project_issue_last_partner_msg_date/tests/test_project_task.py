from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class ProjectTaskTC(TransactionCase):
    def _send_partner_email(self, task):
        params = {
            "body": "Test message",
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
            "author_id": task.partner_id.id,
        }
        return task.message_post(**params)

    def test_create(self):
        date = "2025-01-01 00:00:00"

        task1 = self.env.ref("project.project_1_task_1").copy()  # calls create
        task2 = self.env.ref("project.project_1_task_1").copy(
            {"last_partner_msg_date": date}
        )

        self.assertEqual(task1.last_partner_msg_date, task1.create_date)
        self.assertEqual(fields.Datetime.to_string(task2.last_partner_msg_date), date)

    def test_message_post(self):
        task = self.env.ref("project.project_1_task_1")
        msg = self._send_partner_email(task)

        self.assertEqual(task.last_partner_msg_date, msg.create_date)
        self.assertTrue(task.last_partner_msg_date > task.create_date)
