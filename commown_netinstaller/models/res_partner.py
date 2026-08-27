from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    netinstaller_exec_default_script = fields.Boolean(
        default=True,
        string="Execute default netinstaller post-install script?",
    )

    netinstaller_scripts = fields.Many2many(
        "commown_netinstaller.post_install_script",
        string="Netinstaller post install scripts",
    )

    netinstaller_encryption_method = fields.Selection(
        [("luks", "LUKS")],
        string="Encryption method (if any)",
        required=False,
    )

    netinstaller_encryption_master_key_url = fields.Char(
        string="Master key URL",
        help="If this company uses a LUKS master key (Linux only), paste its Passbolt URL here",
    )

    def netinstaller_post_install_scripts(self):
        self.ensure_one()
        scripts = self.env["commown_netinstaller.post_install_script"]

        partner = self.commercial_partner_id
        if partner.netinstaller_exec_default_script:
            scripts |= self.env.ref("commown_netinstaller.default_post_install_script")

        scripts |= partner.netinstaller_scripts

        return scripts
