from odoo.tests import TransactionCase, tagged

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
