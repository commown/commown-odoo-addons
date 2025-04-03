import json

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.queue_job.tests.common import trap_jobs


class AutomatedControlTC(TransactionCase):
    def setUp(self):
        super().setUp()

        self.control = self._create_control()

    def _create_control(self, filter_pre_domain=None):
        vals = {
            "name": "Test control",
            "model_id": self.env.ref("project.model_project_task").id,
            "filter_domain": '[("project_id", "=", 1)]',
            "user_message": "Test Error",
        }

        if filter_pre_domain is not None:
            vals["filter_pre_domain"] = filter_pre_domain

        return self.env["commown_automated_control.automated_control"].create(vals)

    def get_notify(self, old_infos=None, level="info"):
        param_name = "notify_" + level + "_channel_name"
        name = json.dumps(getattr(self.env.user, param_name))
        objs = self.env["bus.bus"].search([("channel", "=", name)], order="id")
        msgs = [json.loads(m)["message"] for m in objs.mapped("message")]
        return msgs[len(old_infos or ()) :]

    def test_onchange_model_id(self):
        # Pre-requisite
        self.assertEqual(self.control.model_name, "project.task")

        # Change model
        self.control.update(
            {
                "model_id": self.env.ref("crm.model_crm_lead"),
                "filter_domain": '[("team_id", "=", 1)]',
            }
        )
        self.control.onchange_model_id()

        # Check results
        self.assertEqual(self.control.model_name, "crm.lead")

    def test_compute_automation_name(self):
        self.assertEqual(
            self.control._compute_automation_name(self.control.name),
            "[Commown][Automated Control] Test control",
        )
        self.control.name = "New name"

        self.env.cache.invalidate()
        self.assertEqual(
            self.control.base_automation_id.name,
            "[Commown][Automated Control] New name",
        )

    def test_check_filter_pre_domain_is_defined(self):
        # Test on create
        old_infos = self.get_notify(level="warning")
        self._create_control(filter_pre_domain='["id", "=", 1]')
        new_infos = self.get_notify(old_infos, "warning")
        self.assertFalse(new_infos)

        self._create_control(filter_pre_domain=None)
        new_infos = self.get_notify(old_infos, "warning")
        self.assertEqual(
            new_infos,
            ["This could lead to unexpected results"],
        )

        # Test on write
        old_infos = self.get_notify(level="warning")
        self.control.filter_pre_domain = '["id", "=", 1]'
        new_infos = self.get_notify(old_infos, "warning")
        self.assertFalse(new_infos)

        self.control.filter_pre_domain = "[]"
        new_infos = self.get_notify(old_infos, "warning")
        self.assertEqual(
            new_infos,
            ["This could lead to unexpected results"],
        )

    def test_check_domain_restrictivity(self):
        with self.assertRaises(ValidationError) as err:
            self.control.filter_domain = False
        self.assertIn("Application domain is mandatory", err.exception.name)

        # Check Pre-requisite
        self.assertEqual(self.control.model_name, "project.task")

        expected_message = "Domain is not restrictive enough. Please add a Project"
        with self.assertRaises(ValidationError) as err:
            self.control.filter_domain = '[("stage_id", "=", 1)]'
        self.assertEqual(expected_message, err.exception.name)

    def test_execute_raise(self):
        user_internal = self.env.ref("base.user_demo")
        user_root = self.env.ref("base.user_root")
        self.env.ref("commown_automated_control.group_manager").users |= (
            user_root + user_internal
        )
        record = self.env["project.task"].search([])[0]

        self.assertEqual(self.control.behaviour, "raise")
        expected_message = (
            "Test Error\n\n\nThis message comes from automated control"
            ' "Test control" (id: %s)\nRaised by %s' % (self.control.id, record)
        )
        with self.assertRaises(UserError) as err:
            self.control.with_user(user_internal).execute(record)
        self.assertEqual(err.exception.args[0], expected_message)

        with trap_jobs() as trap:
            self.control.with_user(user_root).execute(record)
        trap.assert_jobs_count(1, only=self.control._raise_warning)
        with self.assertRaises(UserError) as err:
            trap.perform_enqueued_jobs()
        self.assertEqual(err.exception.args[0], expected_message)

    def test_execute_notify(self):
        self.control.behaviour = "notify"

        old_infos = self.get_notify()
        self.control.execute(self.env["project.task"].search([])[0])
        new_infos = self.get_notify(old_infos)

        self.assertEqual(
            new_infos,
            ["Test Error"],
        )

    def test_base_automation(self):
        self.env.cache.invalidate()
        self.assertEqual(
            self.control.base_automation_id.automated_control_id, self.control
        )

    def test_active_switch(self):
        self.assertTrue(self.control.active)
        self.assertTrue(self.control.base_automation_id.active)

        self.control.active = False
        self.env.cache.invalidate()
        self.assertFalse(self.control.base_automation_id.active)

        self.control.active = True
        self.env.cache.invalidate()
        self.assertTrue(self.control.base_automation_id.active)
