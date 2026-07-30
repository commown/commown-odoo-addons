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
