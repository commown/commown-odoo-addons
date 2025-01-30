from odoo.exceptions import AccessError
from odoo.tests.common import SingleTransactionCase


class SecurityTC(SingleTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref("commown_automated_control.group_manager") + cls.env.ref(
            "base.group_user"
        )
        cls.user_control_manager = cls.env["res.users"].create(
            {
                "name": "Test control manager",
                "login": "login",
                "groups_id": [(6, 0, groups.ids)],
                "user_type": "internal",
            }
        )
        cls.user_no_access = cls.env["res.users"].create(
            {
                "name": "Test no access",
                "login": "login2",
                "groups_id": [(6, 0, cls.env.ref("base.group_user").ids)],
            }
        )
        cls.control = cls.create_control()

    @classmethod
    def create_control(cls, as_user=False):
        model = cls.env["commown_automated_control.automated_control"]

        if as_user:
            model = model.sudo(as_user.id)

        return model.create(
            {
                "name": "Test control",
                "model_id": cls.env.ref("project.model_project_task").id,
                "filter_domain": '[("project_id", "=", 1)]',
                "user_message": "Test Error",
            }
        )

    def test_can_create(self):
        control = self.create_control(as_user=self.user_control_manager)
        self.assertTrue(control)

        with self.assertRaises(AccessError) as err:
            self.create_control(as_user=self.user_no_access)
        self.assertIn(
            "Sorry, you are not allowed to create this kind of document",
            err.exception.name,
        )

    def test_can_read(self):
        self.assertEqual(
            self.control.sudo(self.user_control_manager.id).name,
            "Test control",
        )
        with self.assertRaises(AccessError) as err:
            self.control.sudo(self.user_no_access.id).name
        self.assertIn(
            "Sorry, you are not allowed to access this document",
            err.exception.name,
        )

    def test_can_write(self):
        new_name = "New Name"
        with self.assertRaises(AccessError) as err:
            self.control.sudo(self.user_no_access.id).name = new_name
        self.assertIn(
            "Sorry, you are not allowed to modify this document",
            err.exception.name,
        )

        self.control.sudo(self.user_control_manager.id).name = new_name
        self.assertEqual(
            self.control.name,
            new_name,
        )

    def test_can_unlink(self):
        control = self.create_control()
        with self.assertRaises(AccessError) as err:
            control.sudo(self.user_no_access.id).unlink()
        self.assertIn(
            "Sorry, you are not allowed to delete this document",
            err.exception.name,
        )

        base_automation = control.base_automation_id
        control.sudo(self.user_control_manager.id).unlink()
        self.assertFalse(control.exists())
        self.assertFalse(base_automation.exists())
