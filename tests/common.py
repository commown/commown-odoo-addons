import json
import os.path as osp
from base64 import b64decode
from email import encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from io import StringIO
from urllib.parse import urlparse

from odoo.tests.common import TransactionCase
from PyPDF2 import PdfFileReader  # dunno how to declare test deps in odoo?

HERE = osp.dirname(__file__)


def pdf_page_num(ir_attachment):
    pdf = PdfFileReader(StringIO(b64decode(ir_attachment.datas)))
    return pdf.getNumPages()


class FakeResponse(object):
    def __init__(self, json_data, pdf_data):
        self.json_data = json_data
        self.pdf_data = pdf_data
        self.headers, self.content = self._build()

    def raise_for_status(self):
        pass

    def _build(self):
        msg = MIMEMultipart()

        json_part = MIMEBase("application", "json")
        json_part.set_payload(json.dumps(self.json_data))
        msg.attach(json_part)

        pdf_part = MIMEBase("application", "octet-stream")
        pdf_part.set_payload(self.pdf_data)
        encoders.encode_base64(pdf_part)
        msg.attach(pdf_part)

        msg_text = msg.as_string()
        boundary = msg.get_boundary()
        headers = {"Content-Type": 'multipart/mixed; boundary="%s"' % boundary}
        part_marker = "--" + boundary
        content = part_marker + msg_text.split(part_marker, 1)[1]
        return headers, content


class BaseShippingTC(TransactionCase):
    def setUp(self):
        super(BaseShippingTC, self).setUp()
        fake_meta_data = {"labelResponse": {"parcelNumber": "6X0000000000"}}
        with open(osp.join(HERE, "fake_label.pdf")) as fobj:
            self.fake_label_data = fobj.read()
        self.fake_resp = FakeResponse(fake_meta_data, self.fake_label_data)
        self.shipping_account = self.env["keychain.account"].create(
            {
                "namespace": "colissimo",
                "name": "Colissimo standard",
                "technical_name": "colissmo-std",
                "login": "ColissimoLogin",
                "clear_password": "test",
            }
        )
        self.parcel_type = self.env.ref("commown_shipping.fp2-outward-ins300")

    def assertEqualFakeLabel(self, ir_attachment):
        self.assertEqual(b64decode(ir_attachment.datas), self.fake_label_data)

    def _attachment_from_download_action(self, download_action):
        return self.env["ir.attachment"].browse(
            int(urlparse(download_action["url"]).path.rsplit("/", 1)[-1])
        )
