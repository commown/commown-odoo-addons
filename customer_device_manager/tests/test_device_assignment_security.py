from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase


class TestDeviceAssignmentSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner1 = cls.env.ref("base.res_partner_address_15")
        cls.partner2 = cls.env.ref("base.res_partner_address_16")
        cls.company = cls.env.ref("base.res_partner_1")
        cls.other_company = cls.company.copy()
        assert cls.company.is_company
        assert cls.other_company.is_company

        cls.partner1.parent_id = cls.company.id
        cls.partner2.parent_id = cls.company.id

        cls.group_assigner = cls.env.ref(
            "customer_device_manager.group_customer_device_assigner"
        )
        cls.group_portal = cls.env.ref("base.group_portal")
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_user_manager = cls.env.ref(
            "customer_device_manager.group_user_manager"
        )

        cls.portal_user_insider = cls.create_user(
            "login1-NOMATTER", cls.group_portal, parent_id=cls.company.id
        )
        cls.portal_user_outsider = cls.create_user(
            "login2-NOMATTER", cls.group_portal, parent_id=cls.other_company.id
        )
        cls.portal_user_b2c = cls.create_user(
            "login3-NOMATTER", cls.group_portal, parent_id=False
        )

        cls.assigner_user_insider = cls.create_user(
            "login4-NOMATTER", cls.group_assigner, parent_id=cls.company.id
        )
        cls.assigner_user_outsider = cls.create_user(
            "login5-NOMATTER", cls.group_assigner, parent_id=cls.other_company.id
        )
        cls.assigner_user_b2c = cls.create_user(
            "login6-NOMATTER", cls.group_assigner, parent_id=False
        )

        cls.internal_user = cls.create_user(
            "login7-NOMATTER", cls.group_user, parent_id=False
        )
        cls.internal_user_manager = cls.create_user(
            "login8-NOMATTER", cls.group_user_manager, parent_id=False
        )

        cls.product_tmpl = cls.env["product.template"].create(
            {
                "name": "Test Product",
                "type": "product",
                "tracking": "serial",
            }
        )
        cls.product = cls.product_tmpl.product_variant_id
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "Test lot",
                "product_id": cls.product.id,
            }
        )
        cls.assignment = cls.env["customer_device_manager.device_assignment"].create(
            {
                "device_id": cls.lot.id,
                "partner_id": cls.partner1.id,
                "assignment_date": fields.Datetime.now(),
            }
        )

        cls.history_record = cls.env[
            "customer_device_manager.device_assignment_history"
        ].create(
            {
                "assignment_id": cls.assignment.id,
                "date": fields.Datetime.now(),
                "partner_id": cls.partner1.id,
            }
        )

    @classmethod
    def create_user(cls, login, group, **kwargs):
        kwargs.setdefault("name", "test-partner")
        partner = cls.env["res.partner"].create(kwargs)

        return cls.env["res.users"].create(
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
            .with_user(user)
            .search([("id", "=", self.assignment.id)])
        )

    def update_assignment(self, user, partner):
        self.assignment.with_user(user).update({"partner_id": partner.id})

    def can_see_assignment_history(self, user):
        return (
            self.env["customer_device_manager.device_assignment_history"]
            .with_user(user)
            .search([("id", "=", self.history_record.id)])
        )

    def test_rule_device_assignment_portal(self):
        """
        Portal users should only read assignments of their company, and should not be able to update them.
        """
        self.assertFalse(self.can_see_assignment(self.portal_user_b2c))
        self.assertTrue(self.can_see_assignment(self.portal_user_insider))
        self.assertFalse(self.can_see_assignment(self.portal_user_outsider))

        fresh_portal_user_insider = self.create_user(
            "login-fresh-portal", self.group_portal, parent_id=self.company.id
        )

        with self.assertRaises(AccessError):
            self.update_assignment(fresh_portal_user_insider, self.partner2)

    def test_rule_device_assignment_assigner(self):
        """
        Device assigners should only read assignments of their company, and should be able to update the ones 'at_customer'.
        """
        self.assertFalse(self.can_see_assignment(self.assigner_user_b2c))
        self.assertTrue(self.can_see_assignment(self.assigner_user_insider))
        self.assertFalse(self.can_see_assignment(self.assigner_user_outsider))

        self.update_assignment(self.assigner_user_insider, self.partner2)

        fresh_assigner_user_outsider = self.create_user(
            "login-fresh-assigner-outsider",
            self.group_assigner,
            parent_id=self.other_company.id,
        )

        with self.assertRaises(AccessError):
            self.update_assignment(fresh_assigner_user_outsider, self.partner2)

        self.assignment.device_location = "at_commown"
        with self.assertRaises(AccessError):
            self.update_assignment(self.assigner_user_insider, self.partner2)

    def test_access_device_assignment_internal_user(self):
        """
        Internal users should be able to read all assignments, but not update them.
        """
        self.assertTrue(self.can_see_assignment(self.internal_user))

        with self.assertRaises(AccessError):
            self.update_assignment(self.internal_user, self.partner2)

    def test_rule_device_assignment_manager(self):
        "User managers should be able to update and create all assignments"
        self.update_assignment(self.internal_user_manager, self.partner2)

        assignment = (
            self.env["customer_device_manager.device_assignment"]
            .with_user(self.internal_user_manager)
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
            .with_user(self.internal_user_manager)
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
            self.history_record.with_user(fresh_assigner_user_outsider).update(
                {"partner_id": self.partner2.id}
            )

    def test_rule_device_assignment_history_manager(self):
        "User managers should be able to read all history, but not update it."
        self.assertTrue(self.can_see_assignment_history(self.internal_user_manager))

        fresh_internal_user_manager = self.create_user(
            "login-fresh-internal-manager", self.group_user_manager, parent_id=False
        )

        self.history_record.with_user(fresh_internal_user_manager).update(
            {"partner_id": self.partner2.id}
        )
        self.assertTrue(
            self.env["customer_device_manager.device_assignment_history"]
            .with_user(fresh_internal_user_manager)
            .search([("id", "=", self.history_record.id)])
        )

    def test_rule_stock_production_lot_portal(self):
        "Portal users should only read their company's devices."
        self.assertTrue(
            self.env["stock.lot"]
            .with_user(self.assigner_user_insider)
            .search([("id", "=", self.lot.id)])
        )
        self.assertFalse(
            self.env["stock.lot"]
            .with_user(self.assigner_user_outsider)
            .search([("id", "=", self.lot.id)])
        )
        self.assertFalse(
            self.env["stock.lot"]
            .with_user(self.assigner_user_b2c)
            .search([("id", "=", self.lot.id)])
        )
