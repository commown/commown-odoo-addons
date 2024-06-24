from odoo.tests import SavepointCase


class PortalIrRulesTC:
    "Base test class for portal user access-rules-related tests"

    obj = None  # To be overriden by the object we want to test the access to
    children = None  # To be overriden by children of the tested object, if any
    allowed_group_ref = None  # To be overriden by xml ref of the allowed customer group

    def seen(self, entities, user):
        return self.env[entities._name].sudo(user).search([]) & entities

    def _give_portal_access(self, partner):
        model = self.env["portal.wizard"].with_context(active_ids=[partner.id])
        portal_wizard = model.sudo().create({})
        portal_wizard.user_ids.update({"in_portal": True})
        portal_wizard.action_apply()
        self.assertTrue(partner.user_ids)
        return partner.user_ids[0]

    def give_instance_to(self, partner):
        "By default, make partner follow the test object. May be overriden"
        self.env["mail.followers"].create(
            {
                "res_id": self.obj.id,
                "res_model": self.obj._name,
                "partner_id": partner.id,
            }
        )

    def test_directly_owned_object(self):
        "Portal users who follow the object directly must have read access to it"
        self.assertFalse(self.seen(self.obj, self.user1))
        if self.children:
            self.assertFalse(self.seen(self.children, self.user1))

        self.give_instance_to(self.user1.partner_id)

        self.assertTrue(self.seen(self.obj, self.user1))
        if self.children:
            self.assertTrue(self.seen(self.children, self.user1))

    def test_in_customer_allowed_group(self):
        "Portal users belonging to the dedicated customer group must see the object"

        self.assertFalse(self.seen(self.obj, self.user1))
        self.assertFalse(self.seen(self.obj, self.user2))
        if self.children:
            self.assertFalse(self.seen(self.children, self.user1))
            self.assertFalse(self.seen(self.children, self.user2))

        customer_grp = self.env.ref(self.allowed_group_ref)
        customer_grp.users |= self.user2

        self.assertFalse(self.seen(self.obj, self.user1))
        self.assertTrue(self.seen(self.obj, self.user2))
        if self.children:
            self.assertFalse(self.seen(self.children, self.user1))
            self.assertTrue(self.seen(self.children, self.user2))


class PortalInvoiceIrRulesTC(PortalIrRulesTC, SavepointCase):
    "Test class for portal user invoice-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_accounting"

    def setUp(self):
        super().setUp()
        self.obj = self.env.ref("l10n_generic_coa.demo_invoice_1")
        self.children = self.obj.invoice_line_ids

        partner1 = self.obj.partner_id.child_ids[0]
        self.user1 = self._give_portal_access(partner1)

        partner2 = self.obj.partner_id.child_ids[1]
        self.user2 = self._give_portal_access(partner2)

        self.assertNotIn(partner1, self.obj.message_partner_ids)
        self.assertNotIn(partner2, self.obj.message_partner_ids)

    def give_instance_to(self, partner):
        """For invoices, we use the partner_id field instead of followers
        because contract do not add the partner as a follower.
        """
        self.obj.partner_id = partner.id


class PortalSaleOrderIrRulesTC(PortalIrRulesTC, SavepointCase):
    "Test class for portal user sale_order-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_purchase"

    def setUp(self):
        super().setUp()
        self.obj = self.env.ref("sale.portal_sale_order_1")
        self.children = self.obj.order_line

        partner1 = self.obj.partner_id
        partner1.parent_id = self.env.ref("base.res_partner_1")
        self.user1 = self._give_portal_access(partner1)

        partner2 = partner1.copy()
        self.user2 = self._give_portal_access(partner2)

        self.assertNotIn(partner1, self.obj.message_partner_ids)
        self.assertNotIn(partner2, self.obj.message_partner_ids)


class PortalProjectTaskIrRulesTC(PortalIrRulesTC, SavepointCase):
    "Test class for portal user project_task-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_it_support"

    def setUp(self):
        super().setUp()
        ref = self.env.ref

        partner1 = ref("base.partner_demo_portal").copy({"email": "test1@example.com"})
        partner1.parent_id = ref("base.res_partner_1")
        self.user1 = self._give_portal_access(partner1)

        partner2 = partner1.copy({"email": "test2@example.com"})
        self.user2 = self._give_portal_access(partner2)

        project = ref("project.project_project_1")
        project.portal_visibility_extend_to_group_ids |= ref(self.allowed_group_ref)
        self.obj = self.env["project.task"].create(
            {
                "name": "test task",
                "project_id": project.id,
                "partner_id": partner1.parent_id.id,
            }
        )

        self.assertNotIn(partner1, self.obj.message_partner_ids)
        self.assertNotIn(partner2, self.obj.message_partner_ids)

    def test_allow_all_portal_when_no_group_restriction(self):
        self.obj.project_id.portal_visibility_extend_to_group_ids = False
        self.assertTrue(self.seen(self.obj, self.user1))
        self.assertTrue(self.seen(self.obj, self.user2))

    def test_check_no_regression_with_non_portal_projects(self):
        "Project with privacy_visibility!=portal should not be affected by new rules"

        self.obj.project_id.privacy_visibility = "employees"
        customer_grp = self.env.ref(self.allowed_group_ref)
        customer_grp.users |= self.user1
        self.assertFalse(self.seen(self.obj, self.user1))
