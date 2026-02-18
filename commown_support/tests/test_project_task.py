from contextlib import contextmanager
from unittest import mock

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.commown_res_partner_sms.models.common import normalize_phone
from odoo.addons.queue_job.tests.common import trap_jobs


class NoSMSAssertMixin:
    @contextmanager
    def assertNoSMSLogged(self):
        chan = "odoo.addons.commown_support.models.project_task"
        with self.assertLogs(chan, level="WARNING") as logged:
            yield
        self.assertEqual(len(logged.output), 1)
        self.assertIn("No SMS reminder sent", logged.output[0])


@tagged("-at_install", "post_install")
class ProjectTaskModelTC(NoSMSAssertMixin, TransactionCase):
    def test_followup_view(self):
        project = self.env.ref("commown_support.support_project")
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
        task_user = self.env["project.task"].with_user(demo_user).browse(task.id)
        self.assertEqual(task_user.name, "Commown test")
        self.assertEqual(task_user.internal_followup, "<p>Coucou</p>")

        task_portal = (
            self.env["project.task"].with_user(partner.user_ids).browse(task.id)
        )
        self.assertEqual(task_portal.name, "Commown test")
        with self.assertRaises(AccessError) as err:
            task_portal.internal_followup  # pylint: disable=pointless-statement
        self.assertIn("not have enough rights to access", err.exception.args[0])
        self.assertIn("internal_followup", err.exception.args[0])


@tagged("-at_install", "post_install")
class ProjectTaskActionTC(NoSMSAssertMixin, TransactionCase):
    def flush_tracking(self):
        """Force the creation of tracking values."""
        self.env.flush_all()
        self.cr.precommit.run()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env.ref("commown_support.support_project")

        # Adapt defined stages to our needs: use expected name
        # conventions and remove email model as they are buggy for
        # issues (their template model is task instead, which leads to
        # crashes)
        cls.stage_pending = cls.env["project.task.type"].create(
            {"name": "Working on it [after-sale: pending]", "mail_template_id": False}
        )
        cls.stage_pending.project_ids |= cls.project
        cls.stage_wait = cls.stage_pending.copy(
            {"name": "Wait [after-sale: waiting-customer]", "mail_template_id": False}
        )
        cls.stage_reminder = cls.stage_pending.copy(
            {
                "name": "Remind email [after-sale: reminder-email]",
                "mail_template_id": False,
            }
        )
        cls.stage_end_ok = cls.stage_pending.copy(
            {"name": "Solved [after-sale: end-ok]", "mail_template_id": False}
        )
        cls.stage_manual = cls.stage_pending.copy(
            {"name": "Solved [after-sale: manual]", "mail_template_id": False}
        )
        cls.stage_sending_pieces = cls.stage_pending.copy(
            {
                "name": "Sending Pieces [after-sale: sending-pieces-ongoing]",
                "mail_template_id": False,
            }
        )
        cls.stage_waiting_pieces_return = cls.stage_pending.copy(
            {
                "name": "Waiting Pieces [after-sale: waiting-pieces-return]",
                "mail_template_id": False,
            }
        )

        cls.partner = cls.env.ref("base.partner_demo_portal")
        cls.partner.update({"firstname": "Flo", "phone": "+33747397654"})

        cls.task = cls.env["project.task"].create(
            {
                "name": "Commown test",
                "project_id": cls.project.id,
                "stage_id": cls.stage_pending.id,
                "partner_id": cls.partner.id,
                "user_ids": cls.env.ref("base.user_demo").ids,
            }
        )

    def reset_actions_last_run(self):
        "Unset all commown actions' last_run date"
        action_refs = (
            self.env["ir.model.data"]
            .search(
                [("module", "=", "commown_support"), ("model", "=", "base.automation")]
            )
            .mapped("name")
        )
        for ref in action_refs:
            self.env.ref("commown_support.%s" % ref).last_run = False

    def assertIsReminderEmail(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_comment"))
        self.assertEqual(
            message.subject, "Commown : votre demande d'assistance se languit de vous !"
        )
        self.assertEqual(message.author_id, self.env.ref("base.user_demo").partner_id)

    def assertIsStageChangeMessage(self, message):
        self.assertEqual(message.subtype_id, self.env.ref("project.mt_task_stage"))

    def test_send_reminders(self):
        """A reminder mail to followers and SMS to partner must be sent
        when task is put in the dedicated column.
        """

        message_num = len(self.task.message_ids)
        fr = self.env.ref("base.fr")
        self.task.partner_id.update({"country_id": fr.id, "phone": "+33747397654"})
        with trap_jobs() as trap:
            self.flush_tracking()  # Making sure a tracking discard will not impact next flush

            self.task.update({"stage_id": self.stage_reminder.id})
            self.flush_tracking()
        trap.assert_jobs_count(1, only=self.task.send_sms_from_template)

        # Check email message
        # 2 expected messages: email, stage change (in reverse order)
        self.assertEqual(len(self.task.message_ids), message_num + 2)
        self.assertIsStageChangeMessage(self.task.message_ids[0])
        self.assertIsReminderEmail(self.task.message_ids[1])

        # Check job for sms has been posted
        template = self.env.ref("commown_support.sms_template_issue_reminder")
        country_code = self.task.partner_id.country_id.code
        partner_mobile = normalize_phone(
            self.task.partner_id.get_mobile_phone(),
            country_code,
        )
        with mock.patch(
            "odoo.addons.commown_res_partner_sms.models."
            "mail_thread.MailThread.send_sms_from_template"
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
            self.flush_tracking()  # Making sure a tracking discard will not impact next flush

            self.task.update({"stage_id": self.stage_reminder.id})
            self.flush_tracking()

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

    def _send_partner_email(self, task=None, author_id=None):
        if task is None:
            task = self.task
        self.env["mail.message"].create(
            {
                "author_id": author_id or task.partner_id.id,
                "subject": "Test subject",
                "body": "<p>Test body</p>",
                "message_type": "comment",
                "model": "project.task",
                "res_id": task.id,
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )

    def test_move_task_when_message_arrives_if_not_from_employee(self):
        """When a partner sends a message concerning an task, it moves
        automatically to the pending stage, unless it is an employee.
        """
        self.assertTaskAwakenAction(self.task, self.stage_pending, self.stage_reminder)

    def assertTaskAwakenAction(self, task, stage_pending, stage_reminder):
        employees = self.env.ref("base.group_user")

        # Check test prerequisite
        assert employees not in task.partner_id.mapped("user_ids.groups_id")

        task.update({"stage_id": stage_reminder.id})
        self._send_partner_email(task=task)
        self.assertEqual(task.stage_id, stage_pending)

        with self.assertNoSMSLogged():
            task.update({"stage_id": stage_reminder.id})
        other_partner = self.env.ref("base.partner_demo_portal")
        self._send_partner_email(task=task, author_id=other_partner.id)
        self.assertEqual(task.stage_id, stage_pending)

        other_partner.user_ids.groups_id -= self.env.ref("base.group_portal")
        other_partner.user_ids.groups_id |= employees
        task.update({"stage_id": stage_reminder.id})
        self._send_partner_email(task=task, author_id=other_partner.id)
        self.assertEqual(task.stage_id, stage_reminder)

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
