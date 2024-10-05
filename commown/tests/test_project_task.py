from contextlib import contextmanager

import mock

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, at_install, post_install

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.queue_job.tests.common import trap_jobs


class NoSMSAssertMixin:
    @contextmanager
    def assertNoSMSLogged(self):
        chan = "odoo.addons.commown.models.project_task"
        with self.assertLogs(chan, level="WARNING") as logged:
            yield
        self.assertEqual(len(logged.output), 1)
        self.assertIn("No SMS reminder sent", logged.output[0])


@at_install(False)
@post_install(True)
class ProjectTaskModelTC(NoSMSAssertMixin, TransactionCase):
    def test_followup_view(self):
        project = self.env.ref("commown_self_troubleshooting.support_project")
        project.show_internal_followup = True

        partner = self.env.ref("base.partner_demo_portal")
        task = self.env["project.task"].create(
            {
                "name": "Commown test",
                "project_id": project.id,
                "partner_id": partner.id,
                "internal_followup": "<p>Coucou</p>",
            }
        )
        self.env["mail.followers"].create(
            {
                "partner_id": partner.id,
                "res_id": task.id,
                "res_model": "project.task",
            }
        )

        demo_user = self.env.ref("base.user_demo")
        task_user = self.env["project.task"].sudo(demo_user).browse(task.id)
        self.assertEquals(task_user.name, "Commown test")
        self.assertEquals(task_user.internal_followup, "<p>Coucou</p>")

        task_portal = self.env["project.task"].sudo(partner.user_ids).browse(task.id)
        self.assertEquals(task_portal.name, "Commown test")
        with self.assertRaises(AccessError) as err:
            task_portal.internal_followup
        self.assertIn("security restrictions", err.exception.name)
        self.assertIn("internal_followup", err.exception.name)


@at_install(False)
@post_install(True)
class ProjectTaskActionTC(NoSMSAssertMixin, TransactionCase):
    def setUp(self):
        super(ProjectTaskActionTC, self).setUp()

        self.project = self.env.ref("commown_self_troubleshooting.support_project")

        # Adapt defined stages to our needs: use expected name
        # conventions and remove email model as they are buggy for
        # issues (their template model is task instead, which leads to
        # crashes)
        self.stage_pending = self.env["project.task.type"].create(
            {"name": "Working on it [after-sale: pending]", "mail_template_id": False}
        )
        self.stage_pending.project_ids |= self.project
        self.stage_wait = self.stage_pending.copy(
            {"name": "Wait [after-sale: waiting-customer]", "mail_template_id": False}
        )
        self.stage_reminder = self.stage_pending.copy(
            {
                "name": "Remind email [after-sale: reminder-email]",
                "mail_template_id": False,
            }
        )
        self.stage_end_ok = self.stage_pending.copy(
            {"name": "Solved [after-sale: end-ok]", "mail_template_id": False}
        )
        self.stage_manual = self.stage_pending.copy(
            {"name": "Solved [after-sale: manual]", "mail_template_id": False}
        )
        self.stage_sending_pieces = self.stage_pending.copy(
            {
                "name": "Sending Pieces [after-sale: sending-pieces-ongoing]",
                "mail_template_id": False,
            }
        )
        self.stage_waiting_pieces_return = self.stage_pending.copy(
            {
                "name": "Waiting Pieces [after-sale: waiting-pieces-return]",
                "mail_template_id": False,
            }
        )

        self.partner = self.env.ref("base.partner_demo_portal")
        self.partner.update({"firstname": "Flo", "phone": "+33747397654"})

        self.task = self.env["project.task"].create(
            {
                "name": "Commown test",
                "project_id": self.project.id,
                "stage_id": self.stage_pending.id,
                "partner_id": self.partner.id,
                "user_id": self.env.ref("base.user_demo").id,
            }
        )

    def reset_actions_last_run(self):
        "Unset all commown actions' last_run date"
        action_refs = (
            self.env["ir.model.data"]
            .search([("module", "=", "commown"), ("model", "=", "base.automation")])
            .mapped("name")
        )
        for ref in action_refs:
            self.env.ref("commown.%s" % ref).last_run = False

    def assertIsReminderEmail(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_comment"))
        self.assertEqual(
            message.subject, "Commown : votre demande d'assistance se languit de vous !"
        )
        self.assertEqual(message.author_id, self.env.ref("base.user_demo").partner_id)

    def assertIsReminderSMS(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        self.assertIn("ignorez ce SMS", message.body)

    def assertIsStageChangeMessage(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("project.mt_task_new"))

    def test_send_reminders(self):
        """A reminder mail to followers and SMS to partner must be sent
        when task is put in the dedicated column.
        """

        message_num = len(self.task.message_ids)
        fr = self.env.ref("base.fr")
        self.task.partner_id.update({"country_id": fr.id, "phone": "+33747397654"})
        with trap_jobs() as trap:
            self.task.update({"stage_id": self.stage_reminder.id})
        trap.assert_jobs_count(1, only=self.task.message_post_send_sms_html)

        # Check email message
        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

        # Check job for sms has been posted
        template = self.env.ref("commown.sms_template_issue_reminder")
        country_code = self.task.partner_id.country_id.code
        partner_mobile = normalize_phone(
            self.task.partner_id.get_mobile_phone(),
            country_code,
        )
        with mock.patch(
            "odoo.addons.commown_res_partner_sms.models."
            "mail_thread.MailThread.message_post_send_sms_html"
        ) as post_message:
            trap.perform_enqueued_jobs()
            post_message.assert_called_once_with(
                template,
                self.task,
                numbers=[partner_mobile],
                log_error=True,
            )

    def test_send_reminder_no_sms(self):
        """A reminder SMS must not be sent when a non-employee message
        (interpreted as a message from the partner) has already been sent.
        """

        # Check test prerequisite: task's partner is not an employee
        assert self.env.ref("base.group_user") not in self.task.partner_id.mapped(
            "user_ids.groups_id"
        )

        # Simulate partner sending a message, then put task back to reminder
        self._send_partner_email()
        message_num = len(self.task.message_ids)
        with self.assertNoSMSLogged():
            self.task.update({"stage_id": self.stage_reminder.id})

        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

    def test_move_task_after_expiry(self):
        """After 10 days spent in the reminder stage, crontab should
        automatically move the task into the 'end-ok' stage."""

        self.task.update({"stage_id": self.stage_reminder.id})
        self.task.update({"date_last_stage_update": "2019-01-01 00:00:00"})

        self.reset_actions_last_run()
        self.env["base.automation"]._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_end_ok)

    def _send_partner_email(self, author_id=None):
        self.env["mail.message"].create(
            {
                "author_id": author_id or self.task.partner_id.id,
                "subject": "Test subject",
                "body": "<p>Test body</p>",
                "message_type": "comment",
                "model": "project.task",
                "res_id": self.task.id,
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )

    def test_move_task_when_message_arrives_if_not_from_employee(self):
        """When a partner sends a message concerning an task, it moves
        automatically to the pending stage, unless it is an employee.
        """
        employees = self.env.ref("base.group_user")

        # Check test prerequisite
        assert employees not in self.task.partner_id.mapped("user_ids.groups_id")

        self.task.update({"stage_id": self.stage_reminder.id})
        self._send_partner_email()
        self.assertEqual(self.task.stage_id, self.stage_pending)

        with self.assertNoSMSLogged():
            self.task.update({"stage_id": self.stage_reminder.id})
        other_partner = self.env.ref("base.partner_demo_portal")
        self._send_partner_email(author_id=other_partner.id)
        self.assertEqual(self.task.stage_id, self.stage_pending)

        other_partner.user_ids.groups_id -= self.env.ref("base.group_portal")
        other_partner.user_ids.groups_id |= employees
        self.task.update({"stage_id": self.stage_reminder.id})
        self._send_partner_email(author_id=other_partner.id)
        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_customer_long_waiting_task_to_reminder(self):

        self.task.update({"stage_id": self.stage_wait.id})
        self.task.update({"date_last_stage_update": "2019-01-01 00:00:00"})

        self.reset_actions_last_run()
        self.env["base.automation"]._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_reminder)

    def test_move_long_waiting_manual_followup_to_pending(self):

        self.task.update({"stage_id": self.stage_manual.id})
        self.task.update({"date_last_stage_update": "2019-01-01 00:00:00"})

        self.reset_actions_last_run()
        self.env["base.automation"]._check()  # method called by crontab

        self.assertEqual(self.task.stage_id, self.stage_pending)

    def test_move_manual_long_waiting_task_when_message_arrives(self):
        """When a customer message arrives which concerns a manually
        handled task, the task is moved to the pending stage."""

        self.task.update({"stage_id": self.stage_manual.id})

        self._send_partner_email()

        self.assertEqual(self.task.stage_id, self.stage_pending)

    def test_move_sending_pieces_ongoing_to_pending(self):

        self.task.update({"stage_id": self.stage_sending_pieces.id})
        self.task.update({"date_last_stage_update": "2019-01-01 00:00:00"})

        self.reset_actions_last_run()
        self.env["base.automation"]._check()  # method called by crontab

        self.assertEqual(
            self.task.stage_id, self.stage_pending, self.task.stage_id.name
        )

    def test_move_waiting_pieces_to_pending(self):

        self.task.update({"stage_id": self.stage_waiting_pieces_return.id})
        self.task.update({"date_last_stage_update": "2019-01-01 00:00:00"})

        self.reset_actions_last_run()
        self.env["base.automation"]._check()  # method called by crontab

        self.assertEqual(
            self.task.stage_id, self.stage_pending, self.task.stage_id.name
        )
