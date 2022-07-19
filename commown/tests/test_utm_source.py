from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, at_install, post_install


@at_install(False)
@post_install(True)
class UtmSourceTC(TransactionCase):
    def test_action_merge(self):
        ref = self.env.ref
        source1 = ref("utm.utm_source_search_engine")
        source2 = source1.copy({"name": "test"})
        lead = ref("crm.crm_case_1")
        lead.source_id = source2.id

        self.env["utm.source"].browse((source1.id, source2.id)).action_merge()

        self.assertEqual(lead.source_id, source1)

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
