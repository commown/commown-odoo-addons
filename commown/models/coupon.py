import subprocess
import tempfile
import os.path as osp
import shutil

from odoo import models


COUPON_DEFAULTS = {
    "page_width_mm": 210,
    "page_height_mm": 297,
    "nx": 5,
    "ny": 13,  # number of labels in the x and y dirs
    "w": 38.1,
    "h": 21.2,  # width and height of the labels (mm)
    "x0": 5.0,
    "y0": 11.0,  # pos. of 1st label from sheet corner (mm)
    "dx": 2.5,
    "dy": 0.0,  # gap size between rows and columns (mm)
    "debug": False,  # show debug svg form for each coupon if True
    "PAGE_TEMPLATE": (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg width="%(page_width_mm)dmm" height="%(page_height_mm)dmm"'
        ' viewBox="0 0 %(page_width_mm)d %(page_height_mm)d">\n'
        "%(content)s\n"
        "</svg>"
    ),
    "COUPON_LABEL_TEMPLATE": (
        '<text x="%(cx).2f" y="%(cy).2f" font-size="4px"'
        ' dominant-baseline="middle" text-anchor="middle"'
        ">%(code)s</text>\n"
    ),
    "COUPON_DEBUG_FORM": (
        '<rect x="%(x).2f" y="%(y).2f" width="%(w).2f" height="%(h).2f"'
        ' rx="2" ry="2" stroke-width="0.1" stroke="black" fill="white"/>\n'
    ),
}


def convert_svg_to_pdf(svg_content, settings):
    """ Convert given svg content into a pdf (as bytes) """
    width_in_pt = int(settings["page_width_mm"] / 25.4 * 72)  # 1pt = 1/72 inch
    directory = tempfile.mkdtemp()
    try:
        svg_path = osp.join(directory, "file.svg")
        pdf_path = osp.join(directory, "file.pdf")
        with open(svg_path, "wb") as svg_file:
            svg_file.write(svg_content)
        subprocess.check_call(
            [
                "rsvg-convert",
                "-f",
                "pdf",
                "-a",
                "-w",
                str(width_in_pt),
                "-o",
                pdf_path,
                svg_path,
            ]
        )
        with open(pdf_path) as pdf_file:
            return pdf_file.read()
    finally:
        shutil.rmtree(directory, ignore_errors=True)


class Campaign(models.Model):
    _inherit = "coupon.campaign"

    def _generate_svg(self):
        self.ensure_one()

        # Let a chance to override defaults from action context:
        ctx = COUPON_DEFAULTS.copy()
        for key in ctx:
            if key in self.env.context:
                ctx[key] = self.env.context[key]

        doc_template = ctx["PAGE_TEMPLATE"]
        label_template = ctx["COUPON_LABEL_TEMPLATE"]
        if ctx["debug"]:
            label_template += ctx["COUPON_DEBUG_FORM"]

        Coupon = self.env["coupon.coupon"]
        content = []
        for nb in range(ctx["nx"] * ctx["ny"]):
            i, j = nb % ctx["nx"], nb % ctx["ny"]
            ctx.update(
                {
                    "x": ctx["x0"] + i * (ctx["dx"] + ctx["w"]),
                    "y": ctx["y0"] + j * (ctx["dy"] + ctx["h"]),
                }
            )
            ctx.update({"cx": ctx["x"] + ctx["w"] / 2, "cy": ctx["y"] + ctx["h"] / 2})
            ctx["code"] = Coupon.create({"campaign_id": self.id}).code
            content.append(label_template % ctx)
        ctx["content"] = "\n".join(content)
        return ctx, doc_template % ctx

    def action_generate_and_print_coupons(self):
        self.ensure_one()

        settings, data = self._generate_svg()

        if self.env.context.get("skip_conversion", False):
            mime, name = "image/svg+xml", "labels.svg"
        else:
            mime, name = "application/pdf", "labels.pdf"
            data = convert_svg_to_pdf(data, settings)

        attachment = self.env["ir.attachment"].create(
            {
                "res_model": "coupon.campaign",
                "res_id": self.id,
                "mimetype": mime,
                "datas": data.encode("base64"),
                "datas_fname": name,
                "name": name,
                "public": False,
                "type": "binary",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": attachment.website_url + "&download=1",
            "target": "new",
        }
