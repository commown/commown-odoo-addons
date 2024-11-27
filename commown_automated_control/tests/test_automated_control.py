import json

from odoo.exceptions import ValidationError, Warning
from odoo.tests.common import TransactionCase


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

    def get_infos(self, old_infos=None):
        name = json.dumps(self.env.user.notify_info_channel_name)
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

    def test_execute(self):
        self.assertEqual(self.control.behaviour, "raise")
        expected_message = (
            'Test Error\nThis message comes from automated control "Test control" (id: %s)'
            % self.control.id
        )
        with self.assertRaises(Warning) as err:
            self.control.execute()
        self.assertEqual(err.exception.args[0], expected_message)

        self.control.behaviour = "notify"

        old_infos = self.get_infos()
        self.control.execute()
        new_infos = self.get_infos(old_infos)

        self.assertEqual(
            new_infos,
            ["Test Error"],
        )
