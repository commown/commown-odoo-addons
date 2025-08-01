from odoo_test_helper import FakeModelLoader

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class UtmSourceTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Register the test model:
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        from .models import TestUtmDummy

        cls.loader.update_registry((TestUtmDummy,))

        cls.source1 = cls.env.ref("utm.utm_source_search_engine")
        cls.source2 = cls.source1.copy({"name": "test"})
        cls.dummy_rec = cls.env["test.utm_dummy"].create({"source_id": cls.source1.id})

    def test_action_merge(self):
        self.dummy_rec.source_id = self.source2.id
        self.env["utm.source"].browse((self.source1.id, self.source2.id)).action_merge()

        self.assertEqual(self.dummy_rec.source_id, self.source1)
        self.assertFalse(self.source2.exists())

    def test_action_remove(self):
        with self.assertRaises(UserError):
            self.source1.action_remove()

        self.source2.action_remove()
        self.assertFalse(self.source2.exists())
