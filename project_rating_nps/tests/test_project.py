# Copyright 2020 Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo_test_helper import FakeModelLoader

from odoo.tests.common import TransactionCase


class TestProject(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test project",
                "rating_status": "stage",
            }
        )

    def test_nps(self):
        for num in range(11):
            task = self.env["project.task"].create(
                {
                    "project_id": self.project.id,
                    "name": "Issue Task %d" % num,
                }
            )
        self.assertEqual(self.project.net_promoter_score, False)

        for num, task in enumerate(self.project.task_ids):
            token = task._rating_get_access_token()
            rating = self.env["rating.rating"].search(
                [
                    ("access_token", "=", token),
                ]
            )
            rating.write({"rating": num, "consumed": True})
        self.assertEqual(self.project.net_promoter_score, int(100 * ((2 - 7) / 11.0)))


class TestParentRatingComputeOverload(TransactionCase):
    """
    This test class aims to test the behavior of the _compute_rating_satisfaction_percentage,
    which computes several rating fields but using functions containing an assert instruction,
    which bounds rating scores to be within 0 to 5 (see `odoo/addons/rating/models/rating_data.py`),
    whereas the NPS system should range from 0 to 10.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        from .dummy_models import NPS_DummyModel, NPS_DummyParentModel

        cls.loader.update_registry((NPS_DummyParentModel, NPS_DummyModel))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def test_project_model_ok(self):
        """
        Project model computation shouldn't crash with fields computed with
        _compute_rating_satisfaction_percentage method.
        """
        # Setup
        project = self.env["project.project"].create(
            {"name": "Test project", "rating_status": "stage"}
        )
        task = self.env["project.task"].create(
            {"name": "Test issue", "project_id": project.id}
        )

        # Without any consumed ratings, the project rating count should be 0
        self.assertEqual(project.rating_count, 0)

        # Checking if accessing unused computed values doesn't trigger an exception
        _ = project.rating_percentage_satisfaction
        _ = project.rating_avg
        _ = project.rating_avg_percentage

        # A rate of 8 (outside of 0-5 range but within 0-10 range)
        # shouldn't disrupt rating_count computation.
        token = task._rating_get_access_token()
        rating = self.env["rating.rating"].search([("access_token", "=", token)])

        rating.write({"rating": 8, "consumed": True})
        self.assertEqual(project.rating_count, 1)

    def test_non_project_model_nok(self):
        """
        Models other than project.project shouldn't be affected
        by _compute_rating_satisfaction_percentage overload.
        (ie. raise an Exception due to the assert instruction)
        """
        # Setup
        parent_dummy = self.env["project_rating_nps.dummy.parent.model"].create({})
        dummy = self.env["project_rating_nps.dummy.model"].create(
            {"parent_id": parent_dummy.id}
        )

        token = dummy._rating_get_access_token()
        rating = self.env["rating.rating"].search([("access_token", "=", token)])

        # Out-of-range rating value should trigger assert instruction
        rating.write({"rating": 8, "consumed": True})
        with self.assertRaises(AssertionError):
            _ = parent_dummy.rating_count

        # In-range value should allow regular computation
        rating.write({"rating": 3})
        self.assertEqual(parent_dummy.rating_count, 1)
