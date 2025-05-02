from odoo.tests import TransactionCase


class PortalIrRulesTC:
    "Base test class for portal user access-rules-related tests"

    obj = None  # To be overriden by the object we want to test the access to
    children = None  # To be overriden by children of the tested object, if any
    allowed_group_ref = None  # To be overriden by xml ref of the allowed customer group

    @classmethod
    def check_test_prerequisite(cls, check, msg="Prerequisite failed"):
        "Check the `check` argument is truthy or raise a RuntimeError with give message"
        if not check:
            raise RuntimeError(msg)

    def seen(self, entities, user):
        return self.env[entities._name].with_user(user).search([]) & entities

    @classmethod
    def _give_portal_access(cls, partner):
        partner.ensure_one()
        model = cls.env["portal.wizard"].with_context(active_ids=[partner.id])
        portal_wizard = model.sudo().create({})

        non_portal_users = portal_wizard.user_ids.filtered_domain(
            [("is_portal", "=", False)]
        )
        if non_portal_users:
            non_portal_users.action_grant_access()

        cls.check_test_prerequisite(partner.user_ids)

        return partner.user_ids[0]

    def give_instance_to(self, partner):
        "By default, make partner follow the test object. May be overriden"
        self.obj.message_subscribe([partner.id])

    def test_directly_accessible_object(self):
        """
        Portal users who follow (task/sale) or own (invoices) the object directly
        must have read access to it
        """
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

        self.customer_grp.users |= self.user2

        self.assertFalse(self.seen(self.obj, self.user1))
        self.assertTrue(self.seen(self.obj, self.user2))
        if self.children:
            self.assertFalse(self.seen(self.children, self.user1))
            self.assertTrue(self.seen(self.children, self.user2))


class PortalInvoiceIrRulesTC(PortalIrRulesTC, TransactionCase):
    "Test class for portal user invoice-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_accounting"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.company.chart_template_id:  # pragma: no cover
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:  # pragma: no cover
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
                coa.try_loading(company=cls.env.company, install_demo=True)

        cls.obj = cls.env["account.move"].search(
            [
                ("company_id", "=", cls.env.company.id),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "not in", ["draft", "cancel"]),
            ],
            limit=1,
        )
        cls.check_test_prerequisite(cls.obj.partner_id.commercial_partner_id.is_company)
        cls.children = cls.obj.invoice_line_ids

        partner1 = cls.obj.partner_id.child_ids[0]
        cls.user1 = cls._give_portal_access(partner1)

        partner2 = cls.obj.partner_id.child_ids[1]
        cls.user2 = cls._give_portal_access(partner2)

        cls.check_test_prerequisite(partner1 not in cls.obj.message_partner_ids)
        cls.check_test_prerequisite(partner2 not in cls.obj.message_partner_ids)

        cls.customer_grp = cls.env.ref(cls.allowed_group_ref)

    def give_instance_to(self, partner):
        """For invoices, we use the partner_id field instead of followers
        because contract do not add the partner as a follower.
        """
        self.obj.partner_id = partner.id


class PortalSaleOrderIrRulesTC(PortalIrRulesTC, TransactionCase):
    "Test class for portal user sale_order-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_purchase"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.obj = cls.env.ref("sale.portal_sale_order_1")
        cls.children = cls.obj.order_line
        cls.customer_grp = cls.env.ref(cls.allowed_group_ref)

        cls.obj.partner_id.parent_id = cls.env.ref("base.res_partner_1").id

        partner1 = cls.obj.partner_id.copy({"email": "test1@example.com"})
        cls.user1 = cls._give_portal_access(partner1)

        partner2 = partner1.copy({"email": "test2@example.com"})
        cls.user2 = cls._give_portal_access(partner2)

        cls.check_test_prerequisite(partner1.commercial_partner_id.is_company)
        cls.check_test_prerequisite(partner2.commercial_partner_id.is_company)


class PortalProjectTaskIrRulesTC(PortalIrRulesTC, TransactionCase):
    "Test class for portal user project_task-related access rules"

    allowed_group_ref = "customer_manager_base.group_customer_it_support"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref

        cls.customer_grp = ref(cls.allowed_group_ref)

        partner1 = ref("base.partner_demo_portal").copy({"email": "test1@example.com"})
        partner1.parent_id = ref("base.res_partner_1")
        cls.user1 = cls._give_portal_access(partner1)

        partner2 = partner1.copy({"email": "test2@example.com"})
        cls.user2 = cls._give_portal_access(partner2)

        project = ref("project.project_project_1")
        project.portal_visibility_extend_to_group_ids |= ref(cls.allowed_group_ref)
        cls.obj = cls.env["project.task"].create(
            {
                "name": "test task",
                "project_id": project.id,
                "partner_id": partner1.parent_id.id,
            }
        )

        cls.check_test_prerequisite(partner1 not in cls.obj.message_partner_ids)
        cls.check_test_prerequisite(partner2 not in cls.obj.message_partner_ids)

    def test_allow_all_portal_when_no_group_restriction(self):
        self.obj.project_id.portal_visibility_extend_to_group_ids = False
        self.assertTrue(self.seen(self.obj, self.user1))
        self.assertTrue(self.seen(self.obj, self.user2))

    def test_check_no_regression_with_non_portal_projects(self):
        "Project with privacy_visibility!=portal should not be affected by new rules"

        self.obj.project_id.privacy_visibility = "employees"
        self.customer_grp.users |= self.user1
        self.assertFalse(self.seen(self.obj, self.user1))
