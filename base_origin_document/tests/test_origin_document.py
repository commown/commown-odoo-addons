from odoo_test_helper import FakeModelLoader

from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestOriginDocumentMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestDummyModel

        cls.loader.update_registry((TestDummyModel,))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_document(self):
        doc = self.env.ref("base.partner_demo")
        dummy_obj = self.env["test.dummy.model"].create({"name": "dummy object"})

        dummy_obj.origin_document_id = doc.id
        dummy_obj.origin_document_model = doc._name

        self.assertEqual(dummy_obj.origin_document(), doc)
        self.assertEqual(dummy_obj.origin_document_name, "YourCompany, Marc Demo")
        self.assertEqual(dummy_obj.origin_document_model_name, "Contact")

        action = dummy_obj.action_open_origin_document()
        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["res_id"], doc.id)

        dummy_obj.origin_document_id = False
        self.assertIsNone(dummy_obj.origin_document())
        self.assertFalse(dummy_obj.origin_document_name)
        self.assertFalse(dummy_obj.origin_document_model_name)
        self.assertIsNone(dummy_obj.action_open_origin_document())
