# Copyright 2020-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from .common import RatingTestMixin


class TestRating(RatingTestMixin, TransactionCase):
    def test_apply_rating_error_1(self):
        with self.assertRaises(ValueError) as err:
            self.task.rating_apply(
                12, self.rating.access_token, feedback="test feedback"
            )
        self.assertIn("incorrect rating", err.exception.args[0].lower())

    def test_apply_rating_error_2(self):
        with self.assertRaises(ValueError) as err:
            self.task.rating_apply(6, "invalid token")
        self.assertEqual("Invalid token or rating.", err.exception.args[0])

    def test_compute_rating_text(self):
        self.rating.rating = 8
        self.assertEqual(self.rating.rating_text, "neutral")

        self.rating.rating = 9
        self.assertEqual(self.rating.rating_text, "promoter")

        self.rating.rating = 3
        self.assertEqual(self.rating.rating_text, "detractor")

    def test_compute_rating_image_ok(self):
        self.assertTrue(self.rating.rating_image_url)
        self.assertTrue(self.rating.rating_image)

    def test_compute_rating_image_error_no_raise(self):
        "An OSError while computing the rating image should not crash the rate save"

        # The method should not crash on OSError, so we simulate a file not found:
        with patch("base64.b64encode", side_effect=OSError("read error")):
            chan = "odoo.addons.project_rating_nps.models.rating"
            with self.assertLogs(chan, level="ERROR") as cm:
                self.rating._compute_rating_image()
        expected_message = (
            "Could not load rating image for rating id %d: got 'read error'"
            % self.rating.id
        )
        self.assertEqual("ERROR:%s:%s" % (chan, expected_message), cm.output[0])
        self.assertTrue(self.rating.rating_image_url)
        self.assertFalse(self.rating.rating_image)

    def test_apply_rating_1(self):
        "Check rating_apply override works and uses present module images"

        token = self.rating.access_token

        self.task.rating_apply(self.rating.rating, token, feedback="test feedback")

        msg = self.rating.message_id

        self.assertTrue(msg)
        self.assertIn(msg, self.task.message_ids)
        self.assertIn("/project_rating_nps/static/src/img/rate_8.png", msg.body)
        self.assertIn("test feedback", msg.body)

        self.task.rating_apply(9, token, feedback="test updated feedback")
        self.assertEqual(self.rating.rating, 9.0)
        self.assertIn("test updated feedback", msg.body)
        self.assertIn("/project_rating_nps/static/src/img/rate_9.png", msg.body)

    def test_apply_rating_2(self):
        "Check task kanban state changes with the rating when configured to"

        self.assertEqual(self.task.kanban_state, "normal", "wrong rating initial state")
        self.task.stage_id.auto_validation_kanban_state = True

        self.task.rating_apply(6, self.rating.access_token)
        self.assertEqual(self.task.kanban_state, "done")
