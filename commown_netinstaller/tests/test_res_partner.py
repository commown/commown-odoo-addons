from odoo.tests import Form, TransactionCase, tagged

from .common import NetinstallMixin


@tagged("-at_install", "post_install")
class ResPartnerTC(NetinstallMixin, TransactionCase):
    def test_netinstaller_post_install_script(self):
        partner = self.env.ref("base.res_partner_address_1")

        default_script = self.lref("default_post_install_script")
        custom_script = self.lref("custom_post_install_script")
        get_scripts = partner.netinstaller_post_install_scripts

        self.assertEqual(get_scripts(), default_script)

        partner.commercial_partner_id.netinstaller_exec_default_script = False
        self.assertFalse(get_scripts())

        partner.commercial_partner_id.netinstaller_scripts = custom_script
        self.assertEqual(get_scripts(), custom_script)

        partner.commercial_partner_id.netinstaller_exec_default_script = True
        self.assertEqual(get_scripts(), default_script + custom_script)

    def check_readonly(self, form, field_name, true_or_false):
        self.assertEqual(true_or_false, form._get_modifier(field_name, "readonly"))

    def test_ui_perm_readonly(self):
        """Users not in the netinstaller_customer_manager group should
        not be able to edit partner netinstaller fields in the UI
        """
        user = self.env.ref("base.user_demo")

        partner = self.env.ref("base.res_partner_address_1").with_user(user)

        field_names = [
            f
            for f in partner._fields
            if f.startswith("netinstaller") and f != "netinstaller_fields_readonly"
        ]

        form_view = self.lref("view_partner_form")
        with Form(partner, form_view) as form:
            for field_name in field_names:
                self.check_readonly(form, field_name, True)

        user.groups_id |= self.lref("group_netinstaller_customer_change_manager")
        with Form(partner, form_view) as form:
            for field_name in field_names:
                self.check_readonly(form, field_name, False)
