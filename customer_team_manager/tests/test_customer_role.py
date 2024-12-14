from .common import CustomerTeamManagerAbstractTC


class CustomerRoleTC(CustomerTeamManagerAbstractTC):
    "Test customer_role model methods"

    def _readonly(self, short_role, as_user=None, **with_context):
        role = self.env.ref("customer_team_manager.customer_role_%s" % short_role)
        if as_user:
            role = role.sudo(as_user)
        return role.with_context(**with_context).readonly

    def test_compute_readonly(self):
        user = self.customer_user_admin
        self.assertTrue(self._readonly("admin", user, partner_id=user.partner_id.id))
        self.assertFalse(self._readonly("admin", user))
        self.assertFalse(self._readonly("admin", partner_id=user.partner_id.id))
        self.assertFalse(self._readonly("it", user, partner_id=user.partner_id.id))
