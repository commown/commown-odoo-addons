from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from .common import NetinstallMixin


@tagged("-at_install", "post_install")
class NetinstallerPostInstallScriptTC(TransactionCase, NetinstallMixin):
    "Unittests for the post_install_script model"

    def test_perm_user(self):
        user = self.env.ref("base.user_demo")
        user_script_model = self.env[
            "commown_netinstaller.post_install_script"
        ].with_user(user)

        with self.assertRaises(AccessError):
            user_script_model.search_count([])

        user.groups_id |= self.lref("group_netinstaller_user")
        self.assertTrue(user_script_model.search_count([]))

    def test_perm_manager(self):
        user = self.env.ref("base.user_demo")
        user.groups_id |= self.lref("group_netinstaller_user")

        with self.assertRaises(AccessError):
            self.lref("default_post_install_script").with_user(user).cmd = "./mycmd"

        user.groups_id |= self.lref("group_netinstaller_customer_change_manager")
        self.lref("default_post_install_script").cmd = "./mycmd"
        self.assertEqual(self.lref("default_post_install_script").cmd, "./mycmd")
