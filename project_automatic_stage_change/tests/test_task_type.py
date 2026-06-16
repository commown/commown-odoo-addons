from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class AutomaticChangeTaskTypeTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dest_stage = cls.env["project.task.type"].create({"name": "Dest. stage"})
        cls.stage = cls.env["project.task.type"].create(
            {
                "name": "Test stage",
                "has_timely_stage_change": True,
                "timely_stage_dest": dest_stage.id,
                "timely_stage_change_days": 5,
            }
        )

    def test_dest_stage_constraint(self):
        "If the passive change is activated, a destination stage must be set"
        with self.assertRaises(ValidationError) as exc:
            self.stage.timely_stage_dest = False

        self.assertIn("must set a destination stage", exc.exception.args[0])

    def test_passive_change_days_contraint_not_null(self):
        "If the passive change is activated, the number of days before the passive change can't be null"
        with self.assertRaises(ValidationError) as exc:
            self.stage.timely_stage_change_days = False

        self.assertIn("must set a strictly positive number", exc.exception.args[0])

    def test_passive_chane_days_constraint_strictly_positive(self):
        "If the passive change is activated, the number of days before the passive change can't be negative"
        with self.assertRaises(ValidationError) as exc:
            self.stage.timely_stage_change_days = -5

        self.assertIn("must set a strictly positive number", exc.exception.args[0])
