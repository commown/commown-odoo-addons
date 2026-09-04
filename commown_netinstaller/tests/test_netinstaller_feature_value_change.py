from odoo.exceptions import ValidationError

from .common import NetinstallerContractBasedTC


class NetinstallerFeatureValueContractualChangeTC(NetinstallerContractBasedTC):
    "Feature value contractual change related unit tests"

    def test_date_check(self):
        model = self.env["commown_netinstaller.feature.value.contractual_change"]

        model.create(
            {
                "contract_id": self.contract.id,
                "date": self.contract.date_start,
                "feature_value_id": self.lref("ram-16").id,
            }
        )

        with self.assertRaises(ValidationError) as err:
            model.create(
                {
                    "contract_id": self.contract.id,
                    "date": self.contract.date_start,
                    "feature_value_id": self.lref("ram-8").id,
                }
            )

        self.assertEqual(
            str(err.exception), "More than one value change for RAM at 2030-01-01."
        )
