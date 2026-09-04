from odoo import fields, models


class NetinstallerPostInstallScript(models.Model):
    _name = "commown_netinstaller.post_install_script"
    _description = "Describe a script to be be executed to finalize an OS install"

    git_clone_url = fields.Char(required=True)
    git_branch_name = fields.Char(required=True)
    cmd = fields.Char(required=True)
