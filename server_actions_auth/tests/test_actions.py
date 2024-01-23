from odoo.tests import SavepointCase


class IrActionsServerTC(SavepointCase):
    def setUp(self):
        super().setUp()
        partner_model = self.env.ref("base.model_res_partner")
        self.action = self.env["ir.actions.server"].create(
            {
                "name": "Test server action",
                "model_id": partner_model.id,
                "binding_model_id": partner_model.id,
                "state": "code",
                "code": "record.name",
            }
        )

    def get_action_ids(self, as_user=None):
        model = self.env["ir.actions.server"]
        if as_user:
            model = model.sudo(as_user.id)
        return [a["id"] for a in model.get_bindings("res.partner").get("action", ())]

    def test_without_group(self):
        self.assertIn(self.action.id, self.get_action_ids())

    def test_with_group(self):
        group_ref = "base.group_partner_manager"
        user = self.env.ref("base.user_demo")
        self.assertTrue(user.has_group(group_ref))

        self.action.groups_id |= self.env.ref(group_ref)

        self.assertIn(self.action.id, self.get_action_ids(as_user=user))

        user.groups_id -= self.env.ref(group_ref)
        self.assertNotIn(self.action.id, self.get_action_ids(as_user=user))
