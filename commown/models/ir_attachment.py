# This code is an almost copy of the attachment_indexation module from Odoo
# Credits goes to its author at Odoo SA

import io
import logging

from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

from odoo import models

from odoo.addons.document.models.ir_attachment import FTYPES

FTYPES.append("pdf")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _index_pdf(self, bin_data):
        """Index PDF documents"""
        buf = ""
        if bin_data.startswith(b"%PDF-"):
            f = io.BytesIO(bin_data)
            try:
                resource_manager = PDFResourceManager()
                with io.StringIO() as content, TextConverter(
                    resource_manager, content
                ) as device:
                    logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
                    interpreter = PDFPageInterpreter(resource_manager, device)

                    for page in PDFPage.get_pages(f):
                        interpreter.process_page(page)

                    buf = content.getvalue()

                    # Commown fix to avoid crash in postgress index_content column
                    # update for docs badly converted by pdfminer:
                    buf = buf.replace("\0", " ")

            except Exception:
                pass
        return buf
