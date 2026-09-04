from odoo import fields
from odoo.exceptions import AccessError, ValidationError

from .common import NetinstallerContractBasedTC


class NetinstallerFeatureValueContractualChangeTC(NetinstallerContractBasedTC):
    "Feature value contractual change related unit tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fvc = cls.new_fvc(
            contract_id=cls.contract.id,
            date=cls.contract.date_start,
            feature_value_id=cls.lref("ram-16").id,
        )

    @classmethod
    def new_fvc(cls, **kw):
        return cls.env["commown_netinstaller.feature.value.contractual_change"].create(
            kw
        )

    def test_date_check(self):
        "Creation of impossible to create 2 changes of the same feature and the same date"

        with self.assertRaises(ValidationError) as err:
            self.new_fvc(
                contract_id=self.fvc.contract_id.id,
                date=self.fvc.date,
                feature_value_id=self.fvc.feature_value_id.id,
            )

        self.assertEqual(
            str(err.exception), "More than one value change for RAM at 2030-01-01."
        )

    def test_perm_user(self):
        "Users must belong to the netinstaller user group to read features changes"

        user = self.env.ref("base.user_demo")
        fvc_user_model = self.env[
            "commown_netinstaller.feature.value.contractual_change"
        ].with_user(user)

        with self.assertRaises(AccessError):
            fvc_user_model.search_count([])

        user.groups_id |= self.lref("group_netinstaller_user")
        self.assertTrue(fvc_user_model.search_count([]))

    def test_perm_manager(self):
        """Users must belong to the netinstaller customer manager group to modify
        netinstaller feature value changes.
        """
        user = self.env.ref("base.user_demo")
        user.groups_id |= self.lref("group_netinstaller_user")
        user.groups_id |= self.lref("group_netinstaller_feature_manager")

        with self.assertRaises(AccessError):
            self.fvc.with_user(user).date = "2000-01-01"
        self.assertNotEqual(fields.Date.to_string(self.fvc.date), "2001-01-01")

        user.groups_id |= self.lref("group_netinstaller_customer_change_manager")

        self.fvc.with_user(user).date = "2001-01-01"
        self.assertEqual(fields.Date.to_string(self.fvc.date), "2001-01-01")
