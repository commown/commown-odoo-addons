import json
import os.path as osp
from base64 import b64decode
from io import BytesIO
from urllib.parse import urlparse

from requests_toolbelt.multipart.encoder import MultipartEncoder

from odoo.tests.common import TransactionCase

from ..models.colissimo_utils import BASE_URL

from PyPDF2 import PdfFileReader

HERE = osp.dirname(__file__)


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
