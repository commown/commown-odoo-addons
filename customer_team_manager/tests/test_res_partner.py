from pathlib import Path

from odoo.exceptions import AccessError, ValidationError
from odoo.modules.module import get_resource_path

from .common import CustomerTeamManagerAbstractTC

HERE = (Path(__file__) / "..").resolve()


class ResPartnerTC(CustomerTeamManagerAbstractTC):
    "Test class for partner security and methods"

    def test_fields_view_get(self):
        "Essentially check the syntax is correct and actions are filtered out"

        model_sudo = self.env["res.partner"].sudo(self.customer_user_admin)
        result = model_sudo.fields_view_get(toolbar=True)
        self.assertEqual(
            sorted([a["name"] for a in result["toolbar"]["action"]]),
            ["[commown] Customer users dedicated portal access grant wizard action"],
        )

    def test_compute_default_parent_id(self):
        model = self.env["res.partner"].sudo(self.customer_user_admin)
        result = model._compute_default_parent_id()
        self.assertEqual(result, self.customer_company.id)

    def test_portal_user_create_automatic_company(self):
        "A portal user that creates a partner must create it in its company"

        partner = self.create_partner(sudo_as=self.customer_user_admin, name="F Last")
        self.assertEqual(partner.sudo().parent_id, self.customer_company)

    def test_portal_user_create_cannot_force_company(self):
        "A customer cannot create a partner with a company"

        partner = self.create_partner(
            sudo_as=self.customer_user_admin, name="F Last", parent_id=1
        )

        self.assertEqual(partner.parent_id, self.customer_user_admin.parent_id)

    def test_portal_user_write_cannot_force_partner_company(self):
        "A customer must not be able to change the company of an existing partner"

        partner = self.create_partner(name="F Last")
        with self.assertRaises(AccessError):
            partner.sudo(self.customer_user_admin).parent_id = self.customer_company.id

    def test_portal_user_write_cannot_change_colleagues_company(self):
        "A customer must not be able to change the company of a colleague"

        partner = self.create_partner(sudo_as=self.customer_user_admin, name="F Last")

        with self.assertRaises(AccessError) as err:
            partner.sudo(self.customer_user_admin).parent_id = 1
        self.assertEqual(
            err.exception.name,
            "You are not allowed to perform this operation on this partner",
        )

    def test_write_reset_customer_roles_when_becoming_b2c(self):
        self.assertTrue(self.customer_partner_admin.customer_roles)
        self.customer_partner_admin.parent_id = False
        self.assertFalse(self.customer_partner_admin.customer_roles)
        admin_group = self.env.ref("customer_team_manager.group_customer_admin")
        self.assertNotIn(self.customer_partner_admin.user_ids, admin_group.users)

    def test_portal_user_create_and_write_with_role_ok(self):
        admin_role = self.env.ref("customer_team_manager.customer_role_admin")
        admin = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Admin",
            email="admin@test.coop",
            customer_roles=[(6, 0, admin_role.ids)],
        )
        self.assertEqual(admin.parent_id, self.customer_company)
        self._grant_portal_access(admin)
        self.assertIsAdmin(admin)

        empl = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Empl",
            email="employee@test.coop",
        )
        self.assertEqual(empl.parent_id, self.customer_company)
        self._grant_portal_access(empl)
        self.assertIsUser(empl)

        empl.write({"customer_roles": [(6, 0, admin_role.ids)]})
        self.assertIsAdmin(empl)

        minor_role = self.env.ref("customer_team_manager.customer_role_accounting")
        admin.write({"customer_roles": [(6, 0, minor_role.ids)]})
        self.assertIsUser(admin)

        self.customer_partner_admin.sudo(self.customer_user_admin).write(
            {"customer_roles": [(6, 0, minor_role.ids)]}
        )
        self.assertIsUser(self.customer_user_admin)
        admin_group = self.env.ref("customer_team_manager.group_customer_admin")
        self.assertFalse(self.customer_user_admin in admin_group.users)

    def test_write_email(self):
        "Sale managers can overwrite the partner email, not customer admins"

        empl = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Empl",
            email="employee@test.coop",
        )
        self._grant_portal_access(empl)
        self.assertNotEqual(empl.portal_status, "not_granted")  # test pre-requisite

        # Check setting the email using a sale manager does not raise:
        self.assertTrue(self.env.user.has_group("sales_team.group_sale_manager"))
        empl.email = "i_know_what_i_am_doing@test.coop"

        empl_seen_by_customer = empl.sudo(self.customer_user_admin.id)
        with self.assertRaises(ValidationError) as err:
            empl_seen_by_customer.email = "raises_error@test.coop"
        self.assertEqual(
            err.exception.name,
            "The email of partners having portal access cannot be modified!",
        )

    def test_write_customer_roles_error(self):
        "No one can remove the admin role of last customer admin of a company"

        minor_role = self.env.ref("customer_team_manager.customer_role_accounting")
        empl = self.create_partner(parent_id=self.customer_company.id, name="F C")

        with self.assertRaises(ValidationError) as err:
            self.customer_partner_admin.write(
                {"customer_roles": [(6, 0, minor_role.ids)]}
            )
        self.assertEqual(err.exception.name, "At least one administrator is mandatory")

    def test_revoke_portal_last_customer_admin_error(self):
        "No one can remove the portal access of the last customer admin of a company"

        with self.assertRaises(ValidationError) as err:
            self.customer_partner_admin.action_revoke_portal_access()
        self.assertEqual(err.exception.name, "At least one administrator is mandatory")

    def test_write_active_false_removes_portal_user(self):
        "Setting an employee as inactive should revoke is portal access"

        empl = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Empl",
            email="employee@test.coop",
        )
        self._grant_portal_access(empl)
        self.assertIsUser(empl)

        self.assertEqual(empl.portal_status, "never_connected")

        empl.sudo(self.customer_user_admin).active = False
        self.assertEqual(empl.portal_status, "not_granted")
        self.assertFalse(empl.user_ids)

    def test_rule_unlink_not_granted_to_customers(self):
        "Even group_customer_admin members are not granted unlink permission"

        empl = self.create_partner(sudo_as=self.customer_user_admin, name="New Empl")

        _empl = empl.sudo(self.customer_user_admin)
        with self.assertRaises(AccessError) as err:
            _empl.unlink()

        self.assertIn("res.partner", err.exception.name)
        self.assertIn("Operation: unlink", err.exception.name)

    def test_unlink_cannot_remove_last_company_admin(self):
        "Can not unlink last partner with admin role in its company"

        admin_role = self.env.ref("customer_team_manager.customer_role_admin")
        admin = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Admin",
            email="admin@test.coop",
            customer_roles=[(6, 0, admin_role.ids)],
        )
        self._grant_portal_access(admin)
        self.customer_partner_admin.customer_roles -= admin_role

        # Does not trigger _check_customer_allowed_attrs (which is bad), but is
        # necessary to avoid an foreign key error below when unlinking the partner:
        admin.user_ids.unlink()

        with self.assertRaises(ValidationError) as err:
            admin.unlink()
        self.assertEqual(err.exception.name, "At least one administrator is mandatory")

    def test_portal_user_copy_data(self):
        "Creating a new partner from copy should be easy (and not crash)"
        customer_as_him = self.customer_partner_admin.sudo(self.customer_user_admin)

        attrs = customer_as_him.copy_data()[0]
        colleague = self.create_partner(sudo_as=self.customer_user_admin, **attrs)

        self.assertEqual(colleague.commercial_partner_id, self.customer_company)
        self.assertEqual(
            colleague.customer_roles, self.customer_partner_admin.customer_roles
        )

    def test_grant_and_revoke_portal_access(self):
        "Customer can grant and revoke portal access"

        role_accounting = self.env.ref("customer_team_manager.customer_role_accounting")
        empl = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="J C",
            email="jc@test.coop",
            customer_roles=[(6, 0, role_accounting.ids)],
        )
        self.assertEqual(empl.portal_status, "not_granted")

        self._grant_portal_access(empl)
        self.assertEqual(empl.portal_status, "never_connected")

        empl.action_revoke_portal_access()
        self.assertEqual(empl.portal_status, "not_granted")

        self._grant_portal_access(empl)
        self.assertEqual(empl.portal_status, "never_connected")

        self.simulate_user_login(empl.sudo().user_ids)
        self.assertEqual(empl.portal_status, "already_connected")

        empl.action_revoke_portal_access()
        self.assertEqual(empl.portal_status, "not_granted")

    def test_perm_read_by_company_admin(self):
        admin = self.customer_user_admin
        old_count = self.count_seen_partners(sudo_as=admin)

        colleague = self.create_partner(name="J C", parent_id=self.customer_company.id)
        self.assertEqual(self.count_seen_partners(sudo_as=admin), old_count + 1)

        self.create_partner(name="F C")
        # no change
        self.assertEqual(self.count_seen_partners(sudo_as=admin), old_count + 1)

    def test_first_b2b_user_gets_all_roles_attach_to_company(self):
        "First user becoming member of an company must get all customer roles"

        p1 = self.create_partner(name="P O", email="p1@test.com", parent_id=False)
        p2 = self.create_partner(name="P T", email="p2@test.com", parent_id=False)
        self._grant_portal_access(p1)
        self._grant_portal_access(p2)
        p1.user_ids
        p2.user_ids

        # Check prerequisites
        self.assertFalse(p1.commercial_partner_id.is_company)
        self.assertFalse(p2.commercial_partner_id.is_company)

        customer_company = self.customer_company.copy()
        p1.parent_id = customer_company.id
        p2.parent_id = customer_company.id

        all_roles = self.env["customer_team_manager.customer_role"].search([])
        self.assertEqual(p1.customer_roles, all_roles)
        self.assertFalse(p2.customer_roles)

    def test_first_b2b_user_gets_all_roles_grant_portal_access(self):
        "First member of a company who is granted portal access gets all customer roles"

        company = self.customer_company.copy()
        p1 = self.create_partner(name="P O", email="p1@test.com", parent_id=company.id)
        p2 = self.create_partner(name="P T", email="p2@test.com", parent_id=company.id)

        self._grant_portal_access(p1)
        self._grant_portal_access(p2)

        all_roles = self.env["customer_team_manager.customer_role"].search([])
        self.assertEqual(p1.customer_roles, all_roles)
        self.assertFalse(p2.customer_roles)

    def import_csv(self, fname, sudo_as=None):
        import_model = self._model("base_import.import", sudo_as=sudo_as)
        with (HERE / "data" / fname).open("rb") as fobj:
            wizard = import_model.create(
                {
                    "res_model": "res.partner",
                    "file": fobj.read(),
                    "file_name": fname,
                    "file_type": "text/csv",
                }
            )

        columns = fields = wizard.file.splitlines()[0].decode("utf-8").split(",")
        options = {
            "headers": True,
            "advanced": True,
            "keep_matches": False,
            "encoding": "utf-8",
            "separator": ",",
            "quoting": '"',
            "date_format": "",
            "datetime_format": "",
            "float_thousand_separator": "",
            "float_decimal_separator": ".",
            "fields": [],
        }
        return wizard.do(fields, columns, options)

    def colleagues(self, partner=None):
        partner = partner or self.customer_partner_admin
        return partner.commercial_partner_id.child_ids.filtered(
            lambda p: p.type == "contact" and p.id != partner.id
        )

    def create_xmlid(self, entity, name):
        return self.env["ir.model.data"].create(
            {
                "model": "res.partner",
                "module": "__export__",
                "name": name,
                "res_id": entity.id,
            }
        )

    def _common_test_import_ok(self, fname, sudo_as=None):
        role_accounting = self.env.ref("customer_team_manager.customer_role_accounting")

        empl = self.create_partner(
            name="F C",
            email="fc@test.coop",
            parent_id=self.customer_user_admin.parent_id.id,
            customer_roles=[(6, 0, role_accounting.ids)],
        )
        self.create_xmlid(empl, "res_partner_empl")

        # Check test prerequisite:
        self.assertEqual(self.colleagues(), empl)

        result = self.import_csv(fname, sudo_as=sudo_as)
        self.assertTrue(result.get("ids", None), result)

        # Check result:
        colleagues = self.colleagues()
        self.assertEqual(len(colleagues), 2)

        self.assertIn(empl, colleagues)
        self.assertEqual(empl.firstname, "Flo")
        self.assertEqual(empl.lastname, "Cay")
        self.assertEqual(empl.phone, "+33 1 02 03 04 05")
        self.assertEqual(
            sorted(empl.customer_roles.get_xml_id().values()),
            [
                "customer_team_manager.customer_role_accounting",
                "customer_team_manager.customer_role_it",
            ],
        )
        self.assertEqual(empl.commercial_partner_id, self.customer_company)

        other = colleagues - empl
        self.assertEqual(other.firstname, "Person")
        self.assertEqual(other.lastname, "New")
        self.assertEqual(other.phone, "+33 6 02 03 04 05")
        self.assertEqual(
            sorted(other.customer_roles.get_xml_id().values()),
            ["customer_team_manager.customer_role_fleet_manager"],
        )
        self.assertEqual(other.commercial_partner_id, self.customer_company)

    def test_import_ok_correct_partner(self):
        "Partner import by a customer admin must work and respect security constraints"
        self.create_xmlid(self.customer_company, "res_partner_company")
        self._common_test_import_ok("import.csv", self.customer_user_admin)

    def test_import_ok_override_partner(self):
        "Partner must be overriden when customer admin imports partners"

        # Make company references in the imported data point to a company that is NOT
        # the customer admin's one: this is not authorized and should result in errors
        company = self.customer_company.copy()
        self.create_xmlid(company, "res_partner_company")

        self._common_test_import_ok("import_error.csv", self.customer_user_admin)

    def test_get_import_templates(self):
        "The get_import_templates method should not crash"

        result = self.env["res.partner"].get_import_templates()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        template = result[0].get("template", "")
        self.assertTrue(template.startswith("/"))
        self.assertTrue(bool(get_resource_path(*template[1:].split("/"))))
