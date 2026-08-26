from odoo import Command

from .common import NetinstallerContractBasedTC


class NetinstallerContractTC(NetinstallerContractBasedTC):
    "Contract-related unit tests"

    def test_contract_netinstaller_specs_default(self):
        self.assertEqual(
            self.contract.netinstaller_specs(),
            {
                "RAM": 8,
                "MODEL": "NV4XMB,ME,MZ",
                "post_install_script": [
                    {
                        "git_clone_url": "https://gitlab.com/commown/grantees/install",
                        "git_branch_name": "main",
                        "cmd": "./commownScript.sh -u",
                    }
                ],
            },
        )

    def test_contract_netinstaller_specs_custom_script(self):
        self.partner.commercial_partner_id.write(
            {
                "netinstaller_exec_default_script": False,
                "netinstaller_scripts": [
                    Command.link(self.lref("custom_post_install_script").id)
                ],
            }
        )

        self.assertEqual(
            self.contract.netinstaller_specs(),
            {
                "RAM": 8,
                "MODEL": "NV4XMB,ME,MZ",
                "post_install_script": [
                    {
                        "git_clone_url": "https://git.commown.coop/myscript",
                        "git_branch_name": "main",
                        "cmd": "./launch.sh",
                    }
                ],
            },
        )
