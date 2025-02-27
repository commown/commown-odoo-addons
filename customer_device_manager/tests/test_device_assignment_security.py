from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import SavepointCase


class TestDeviceAssignmentSecurity(SavepointCase):
    def setUp(self):
        super().setUp()

        self.partner1 = self.env.ref("base.res_partner_address_15")
        self.partner2 = self.env.ref("base.res_partner_address_16")
        self.company = self.env.ref("base.res_partner_1")
        self.other_company = self.company.copy()
        self.assertTrue(self.company.is_company)
        self.assertTrue(self.other_company.is_company)

        self.partner1.parent_id = self.company.id
        self.partner2.parent_id = self.company.id

        self.group_assigner = self.env.ref(
            "customer_device_manager.group_customer_device_assigner"
        )
        self.group_portal = self.env.ref("base.group_portal")
        self.group_user = self.env.ref("base.group_user")
        self.group_user_manager = self.env.ref(
            "customer_device_manager.group_user_manager"
        )

        self.portal_user_insider = self.create_user(
            "login1-NOMATTER", self.group_portal, parent_id=self.company.id
        )
        self.portal_user_outsider = self.create_user(
            "login2-NOMATTER", self.group_portal, parent_id=self.other_company.id
        )
        self.portal_user_b2c = self.create_user(
            "login3-NOMATTER", self.group_portal, parent_id=False
        )

        self.assigner_user_insider = self.create_user(
            "login4-NOMATTER", self.group_assigner, parent_id=self.company.id
        )
        self.assigner_user_outsider = self.create_user(
            "login5-NOMATTER", self.group_assigner, parent_id=self.other_company.id
        )
        self.assigner_user_b2c = self.create_user(
            "login6-NOMATTER", self.group_assigner, parent_id=False
        )

        self.internal_user = self.create_user(
            "login7-NOMATTER", self.group_user, parent_id=False
        )
        self.internal_user_manager = self.create_user(
            "login8-NOMATTER", self.group_user_manager, parent_id=False
        )

        self.product_tmpl = self.env["product.template"].create(
            {
                "name": "Test Product",
                "type": "product",
                "tracking": "serial",
            }
        )
        self.product = self.product_tmpl.product_variant_id
        self.lot = self.env["stock.production.lot"].create(
            {
                "name": "Test lot",
                "product_id": self.product.id,
            }
        )
        self.assignment = self.env["customer_device_manager.device_assignment"].create(
            {
                "device_id": self.lot.id,
                "partner_id": self.partner1.id,
                "assignment_date": fields.Datetime.now(),
            }
        )

        self.history_record = self.env[
            "customer_device_manager.device_assignment_history"
        ].create(
            {
                "assignment_id": self.assignment.id,
                "date": fields.Datetime.now(),
                "partner_id": self.partner1.id,
            }
        )

    def create_user(self, login, group, **kwargs):
        kwargs.setdefault("name", "test-partner")
        partner = self.env["res.partner"].create(kwargs)

        return self.env["res.users"].create(
            {
                "name": "test-user",
                "login": login,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [group.id])],
            }
        )

    def can_see_assignment(self, user):
        return (
            self.env["customer_device_manager.device_assignment"]
            .sudo(user)
            .search([("id", "=", self.assignment.id)])
        )

    def update_assignment(self, user, partner):
        self.assignment.sudo(user).update({"partner_id": partner.id})

    def can_see_assignment_history(self, user):
        return (
            self.env["customer_device_manager.device_assignment_history"]
            .sudo(user)
            .search([("id", "=", self.history_record.id)])
        )

    def test_rule_device_assignment_portal(self):
        """
        Portal users should only read active assignments of their company, and should not be able to update them.
        """
        self.assertFalse(self.can_see_assignment(self.portal_user_b2c))
        self.assertTrue(self.can_see_assignment(self.portal_user_insider))
        self.assertFalse(self.can_see_assignment(self.portal_user_outsider))

        self.assignment.active = False
        self.assertFalse(self.can_see_assignment(self.portal_user_insider))
        self.assignment.active = True
        self.assertTrue(self.can_see_assignment(self.portal_user_insider))

        fresh_portal_user_insider = self.create_user(
            "login-fresh-portal", self.group_portal, parent_id=self.company.id
        )

        with self.assertRaises(AccessError):
            self.update_assignment(fresh_portal_user_insider, self.partner2)

    def test_rule_device_assignment_assigner(self):
        """
        Device assigners should only read active assignments of their company, and should be able to update them.
        """
        self.assertFalse(self.can_see_assignment(self.assigner_user_b2c))
        self.assertTrue(self.can_see_assignment(self.assigner_user_insider))
        self.assertFalse(self.can_see_assignment(self.assigner_user_outsider))

        self.assignment.active = False
        self.assertFalse(self.can_see_assignment(self.assigner_user_insider))
        self.assignment.active = True
        self.assertTrue(self.can_see_assignment(self.assigner_user_insider))

        self.update_assignment(self.assigner_user_insider, self.partner2)

        fresh_assigner_user_outsider = self.create_user(
            "login-fresh-assigner-outsider",
            self.group_assigner,
            parent_id=self.other_company.id,
        )

        with self.assertRaises(AccessError):
            self.update_assignment(fresh_assigner_user_outsider, self.partner2)

    def test_rule_device_assignment_internal_user(self):
        """
        Internal users should be able to read all active assignments, but not update them.
        """
        self.assertTrue(self.can_see_assignment(self.internal_user))

        with self.assertRaises(AccessError):
            self.update_assignment(self.internal_user, self.partner2)

        self.assignment.active = False
        self.assertFalse(self.can_see_assignment(self.internal_user))

    def test_rule_device_assignment_manager(self):
        "User managers should be able to update and create all assignments"
        self.update_assignment(self.internal_user_manager, self.partner2)

        assignment = (
            self.env["customer_device_manager.device_assignment"]
            .sudo(self.internal_user_manager)
            .create(
                {
                    "device_id": self.lot.id,
                    "partner_id": self.partner1.id,
                    "assignment_date": fields.Datetime.now(),
                }
            )
        )

        self.assertTrue(
            self.env["customer_device_manager.device_assignment"]
            .sudo(self.internal_user_manager)
            .search([("id", "=", assignment.id)])
        )

    def test_rule_device_assignment_history_portal(self):
        "Portal users should only read history of their company and cannot update it."
        self.assertTrue(self.can_see_assignment_history(self.assigner_user_insider))
        self.assertFalse(self.can_see_assignment_history(self.assigner_user_outsider))
        self.assertFalse(self.can_see_assignment_history(self.assigner_user_b2c))

        fresh_assigner_user_outsider = self.create_user(
            "login-fresh-assigner-outsider",
            self.group_assigner,
            parent_id=self.other_company.id,
        )

        with self.assertRaises(AccessError):
            self.history_record.sudo(fresh_assigner_user_outsider).update(
                {"partner_id": self.partner2.id}
            )

    def test_rule_device_assignment_history_manager(self):
        "User managers should be able to read all history, but not update it."
        self.assertTrue(self.can_see_assignment_history(self.internal_user_manager))

        fresh_internal_user_manager = self.create_user(
            "login-fresh-internal-manager", self.group_user_manager, parent_id=False
        )

        self.history_record.sudo(fresh_internal_user_manager).update(
            {"partner_id": self.partner2.id}
        )
        self.assertTrue(
            self.env["customer_device_manager.device_assignment_history"]
            .sudo(fresh_internal_user_manager)
            .search([("id", "=", self.history_record.id)])
        )

    def test_rule_stock_production_lot_portal(self):
        "Portal users should only read their company's devices."
        self.assertTrue(
            self.env["stock.production.lot"]
            .sudo(self.assigner_user_insider)
            .search([("id", "=", self.lot.id)])
        )
        self.assertFalse(
            self.env["stock.production.lot"]
            .sudo(self.assigner_user_outsider)
            .search([("id", "=", self.lot.id)])
        )
        self.assertFalse(
            self.env["stock.production.lot"]
            .sudo(self.assigner_user_b2c)
            .search([("id", "=", self.lot.id)])
        )
