from odoo_test_helper import FakeModelLoader

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class UtmSourceTC(TransactionCase):
    def test_action_merge(self):
        # Register the test model:
        self.loader = FakeModelLoader(self.env, self.__module__)
        self.loader.backup_registry()

        from .models import TestUtmDummy

        self.loader.update_registry((TestUtmDummy,))

        ref = self.env.ref
        source1 = ref("utm.utm_source_search_engine")
        source2 = source1.copy({"name": "test"})
        rec = self.env["test.utm_dummy"].create({"source_id": source2.id})

        self.env["utm.source"].browse((source1.id, source2.id)).action_merge()

        self.assertEqual(rec.source_id, source1)

    def test_action_remove(self):
        ref = self.env.ref
        source1 = ref("utm.utm_source_search_engine")
        source2 = source1.copy({"name": "test"})

        with self.assertRaises(UserError):
            source1.action_remove()

        try:
            source2.action_remove()
        except Exception as exc:
            self.fail("Source removal raised '%s' unexpectedly" % exc)
