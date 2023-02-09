import contextlib
import json
import os.path as osp
import resource
from base64 import b64decode
from io import BytesIO
from urllib.parse import urlparse

from PyPDF2 import PdfFileReader
from requests_toolbelt.multipart.encoder import MultipartEncoder

from odoo.tests.common import TransactionCase

from ..models.colissimo_utils import BASE_URL

HERE = osp.dirname(__file__)


@contextlib.contextmanager
def unlimited_resource():
    old_limits = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(
        resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    )
    yield
    resource.setrlimit(resource.RLIMIT_AS, old_limits)


def pdf_page_num(ir_attachment):
    pdf = PdfFileReader(BytesIO(b64decode(ir_attachment.datas)))
    return pdf.getNumPages()


def colissimo_resp_ok(json_data, pdf_data):
    enc = MultipartEncoder(
        fields={
            "field1": ("file1", json_data, "application/json"),
            "field2": ("file2", pdf_data, "application/octet-stream"),
        }
    )
    return (
        {"Content-Type": "multipart/mixed; boundary=%s" % enc.boundary_value},
        enc.to_string(),
    )


class BaseShippingTC(TransactionCase):
    def setUp(self):
        super(BaseShippingTC, self).setUp()
        with open(osp.join(HERE, "fake_label.pdf"), "rb") as fobj:
            self.fake_label_data = fobj.read()

        self.shipping_account = self.env["commown.shipping_account"].create(
            {
                "name": "ColissimoPrincipal",
                "account": "987654",
                # "password": "xxxxxx",
            }
        )
        self.parcel_type = self.env.ref("commown_shipping.fp2-outward-ins300")

    def mock_colissimo_ok(self, mocker):
        fake_meta_data = {"labelResponse": {"parcelNumber": "6X0000000000"}}
        headers, body = colissimo_resp_ok(
            json.dumps(fake_meta_data).encode("utf-8"), self.fake_label_data
        )
        mocker.post(BASE_URL + "/generateLabel", content=body, headers=headers)

    def assertEqualFakeLabel(self, ir_attachment):
        self.assertEqual(b64decode(ir_attachment.datas), self.fake_label_data)

    def _attachment_from_download_action(self, download_action):
        return self.env["ir.attachment"].browse(
            int(urlparse(download_action["url"]).path.rsplit("/", 1)[-1])
        )

    def _print_label(self, model, entities, parcel_type, use_full_page_per_label=False):
        wizard = self.env[model].create(
            {
                "shipping_ids": [(6, 0, entities.ids)],
                "parcel_type_id": parcel_type.id,
                "use_full_page_per_label": use_full_page_per_label,
            },
        )

        with unlimited_resource():
            action_multi = wizard.print_label()

        self.assertEqual(action_multi["type"], "ir.actions.act_multi")
        self.assertEqual(
            [a["type"] for a in action_multi["actions"]],
            [
                "ir.actions.act_url",
                "ir.actions.act_window_close",
                "ir.actions.act_view_reload",
            ],
        )

        return self._attachment_from_download_action(action_multi["actions"][0])
