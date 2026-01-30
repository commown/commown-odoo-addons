from odoo.tests import HttpCase


class BackendPassageTC(HttpCase):
    timeout = 12

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = cls.env.ref("base.user_demo")
        cls.portal_user = cls.env.ref("base.demo_user0")

    def get(
        self,
        url,
        data=None,
        json=None,
        headers=None,
        allow_redirects=False,
        assert_code=200,
    ):
        """Perform a GET http request using requests. Complements HttpCase.url_open
        with headers and json"""
        if url.startswith("/"):  # pragma: no cover
            url = self.base_url() + url
        resp = self.opener.get(
            url,
            data=data,
            json=json,
            timeout=self.timeout,
            headers=headers,
            allow_redirects=allow_redirects,
        )
        self.assertEqual(assert_code, resp.status_code)
        return resp
