from odoo.tests import TransactionCase


class CommownProductTemplate(TransactionCase):
    def test_is_user_lang_fr_field(self):
        "The is_user_lang_fr value should be set based on the env. user language."
        # Setup
        en = self.env.ref("base.lang_en")
        tmpl = self.env.ref("product.product_product_1_product_template")

        # Loading the french language if not installed in the base
        # (English is installed by default)
        fr = self.env.ref("base.lang_fr")
        if fr.code not in [
            code for code, _ in self.env["res.lang"].get_installed()
        ]:  # pragma: no cover
            wizard = self.env["base.language.install"].create({"lang_ids": fr.ids})
            wizard.lang_install()

        user_1, user_2 = self.env["res.users"].create(
            [
                {"login": "user_1", "name": "User 1", "lang": en.code},
                {"login": "user_2", "name": "User 2", "lang": fr.code},
            ]
        )

        # Case 1: a user with a non-french language ('en_US')
        self.assertFalse(tmpl.with_user(user_1).is_user_lang_fr)

        # Case 2: a user with the french language
        # (we force a recomputation of the field by emptying the cache)
        tmpl.invalidate_recordset()
        self.assertTrue(tmpl.with_user(user_2).is_user_lang_fr)
