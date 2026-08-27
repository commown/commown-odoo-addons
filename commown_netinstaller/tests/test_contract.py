from datetime import timedelta

from odoo import Command
from odoo.tests import Form

from .common import NetinstallerContractBasedTC


class NetinstallerContractTC(NetinstallerContractBasedTC):
    "Contract-related unit tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.netinstaller_user = cls.env.ref("base.user_demo").copy(
            {"name": "netinstaller user"}
        )
        cls.netinstaller_user.groups_id |= cls.lref("group_netinstaller_user")

    def specs_as_netinstaller_user(self):
        "Get contract specs as a user who is in the netinstaller user group"
        return self.contract.with_user(self.netinstaller_user).netinstaller_specs()

    def test_contract_netinstaller_specs_default(self):
        self.assertEqual(
            self.specs_as_netinstaller_user(),
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
            self.specs_as_netinstaller_user(),
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

    def test_contract_netinstaller_specs_contractual_changes(self):
        change_date = self.contract.date_start + timedelta(days=15)
        self.env["commown_netinstaller.feature.value.contractual_change"].create(
            {
                "contract_id": self.contract.id,
                "date": change_date,
                "feature_value_id": self.lref("ram-16").id,
            }
        )

        date_before = self.contract.date_start + timedelta(days=14)
        self.assertEqual(self.contract.netinstaller_specs(date_before)["RAM"], 8)

        date_after = self.contract.date_start + timedelta(days=15)
        self.assertEqual(self.contract.netinstaller_specs(date_after)["RAM"], 16)

    def test_compute_consolidated_feature_values_through_changes_edition(self):
        """When editing feature changes from contract form, the
        netinstaller_consolidated_feature_value_ids field must automatically update
        without a crash.
        """

        # Journal is required, so we need one to be able to save the contract form:
        self.contract.journal_id = self.env["account.journal"].create(
            {
                "name": "Customer journal",
                "code": "RC",
                "company_id": self.env.company.id,
                "type": "bank",
            }
        )

        # Add a feature change beforehand, that will be removed in the contract
        # edition form to test the netinstaller_consolidated_feature_value_ids field
        # computation:
        self.env["commown_netinstaller.feature.value.contractual_change"].create(
            {
                "contract_id": self.contract.id,
                "date": "2000-01-01",  # in the past
                "feature_value_id": self.lref("ram-16").id,
            }
        )

        self.assertIn(
            self.lref("ram-16"),
            self.contract.netinstaller_consolidated_feature_value_ids,
        )

        # Perform the actual form edition
        form_view = self.lref("contract_contract_customer_form_view")
        with Form(self.contract, view=form_view) as contract_form:
            contract_form.netinstaller_feature_value_change_ids.remove(0)
            contract_form.save()

        self.assertNotIn(
            self.lref("ram-16"),
            self.contract.netinstaller_consolidated_feature_value_ids,
        )

    def test_encryption(self):
        partner = self.contract.commercial_partner_id

        partner.netinstaller_encryption_method = "luks"
        self.assertEqual(
            self.specs_as_netinstaller_user().get("encryption"),
            {"method": "luks"},
        )

        partner.netinstaller_encryption_master_key_url = "https://key.priv/mykey"
        self.assertEqual(
            self.specs_as_netinstaller_user().get("encryption"),
            {"method": "luks", "master_key_url": "https://key.priv/mykey"},
        )
