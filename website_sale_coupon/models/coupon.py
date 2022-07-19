import string
import random
from datetime import datetime

from odoo import models, fields, api


class Campaign(models.Model):
    _name = "coupon.campaign"
    _description = "A coupon campaign that describes the coupon benefits"

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Campaign already exists!"),
    ]

    name = fields.Char("Name", required=True, index=True)
    description = fields.Text("Description")
    date_start = fields.Date("Validity start date", help="Leave empty to start now")
    date_end = fields.Date("Validity end date", help="Leave empty for no end")
    seller_id = fields.Many2one(
        "res.partner", string="Partner who sales the coupons", required=True
    )
    target_product_tmpl_ids = fields.Many2many(
        "product.template", string="Target products", help="(all if empty)"
    )
    is_without_coupons = fields.Boolean(
        string="Is the campaign without coupons?",
        help="If true, the campaign name is the code to be used by customers",
        index=True,
        default=False,
    )
    coupon_ids = fields.One2many(
        "coupon.coupon", "campaign_id", string="Coupons of the campaign", index=True
    )
    emitted_coupons = fields.Integer(
        "Emitted coupons",
        compute="_compute_emitted_coupons",
        store=True,
        compute_sudo=True,
    )
    used_coupons = fields.Integer(
        "Used coupons", compute="_compute_used_coupons", store=False, compute_sudo=True
    )
    can_cumulate = fields.Boolean(
        "Can cumulate with *other* campaigns",
        required=True,
        default=True,
        help="If checked, coupons can be cumulated with another campaign's",
    )
    can_auto_cumulate = fields.Boolean(
        "Can use more than one coupon by sale",
        required=True,
        default=False,
        help="If checked, coupons of the same campaign can be cumulated",
    )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        if self.date_start and self.date_end and self.date_start > self.date_end:
            raise models.ValidationError("Start date must be before end date")

    @api.depends("coupon_ids")
    def _compute_emitted_coupons(self):
        for record in self:
            record.emitted_coupons = len(record.coupon_ids)

    def _compute_used_coupons(self):
        for record in self:
            record.used_coupons = len(record.coupon_ids.filtered("used_for_sale_id"))

    @api.multi
    def is_valid(self, sale_order):
        """Return True if current campaign is valid today (according to its
        start and end dates) for the given sale order (comparing its eligible
        to the sold products).
        """
        self.ensure_one()

        # Check dates
        today = datetime.now().date()
        if self.date_start and self.date_start > today:
            return False
        if self.date_end and self.date_end < today:
            return False

        # Check products
        if self.target_product_tmpl_ids:
            target_product_tmpl_ids = set(pt.id for pt in self.target_product_tmpl_ids)
            sold_product_tmpl_ids = set(
                l.product_id.product_tmpl_id.id
                for l in sale_order.order_line
                if l.product_uom_qty > 0
            )
            if not target_product_tmpl_ids.intersection(sold_product_tmpl_ids):
                return False

        return True


class Coupon(models.Model):
    _name = "coupon.coupon"
    _description = "A coupon that customers can associate to their shop order"

    _sql_constraints = [
        ("code_uniq", "unique (code)", "This coupon code is already used!"),
    ]

    _coupon_code_size = 10
    _coupon_allowed_chars = string.ascii_uppercase + string.digits

    def _compute_default_code(self):
        return "".join(
            random.choice(self._coupon_allowed_chars)
            for _char in range(self._coupon_code_size)
        )

    campaign_id = fields.Many2one(
        "coupon.campaign",
        string="Campaign of the coupon",
        required=True,
        ondelete="cascade",
    )
    code = fields.Char(
        string="Code", size=_coupon_code_size, index=True, default=_compute_default_code
    )
    used_for_sale_id = fields.Many2one(
        "sale.order",
        string="Used for sale",
        index=True,
    )
    reserved_for_sale_id = fields.Many2one(
        "sale.order",
        string="Reserved for sale (admin info only)",
        index=True,
    )
    is_auto_coupon = fields.Boolean(
        related="campaign_id.is_without_coupons",
        readonly=True,
    )

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(Coupon, record).name_get()[0]
            if record.is_auto_coupon:
                name = record.campaign_id.name
            else:
                name = record.code
            result.append((record.id, name))
        return result
