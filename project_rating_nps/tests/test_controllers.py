# Copyright 2020-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import Response

from odoo import http
from odoo.tests.common import HttpCase

from .common import RatingTestMixin


class TestControllers(RatingTestMixin, HttpCase):
    def test_action_open_then_submit_rating(self):
        "Check rating_apply override works and uses present module images"

        test_client = Client(http.root, Response)
        werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}

        response = test_client.get(
            "/rate/%s/7" % self.rating.access_token, environ_base=werkzeug_environ
        )

        doc = html.fromstring(response.data)
        self.assertEqual(
            doc.xpath("//input[@type='radio'][@checked='True']/@value"), ["7"]
        )

        post_values = dict(doc.xpath("//form")[0].form_values())
        post_values["feedback"] = "Nice service, keep on the good work!"

        response = test_client.post(
            "/rate/%s/submit_feedback" % self.rating.access_token,
            environ_base=werkzeug_environ,
            data=post_values,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Thank you, we appreciate your feedback!", response.data)

        self.rating.invalidate_recordset()
        self.assertEqual(self.rating.rating, 7)
        self.assertEqual(self.rating.feedback, post_values["feedback"])

        # Check response in case of get
        response2 = test_client.get(
            "/rate/%s/submit_feedback" % self.rating.access_token,
            environ_base=werkzeug_environ,
        )

        self.assertIn(b"Thank you, we appreciate your feedback!", response2.data)
