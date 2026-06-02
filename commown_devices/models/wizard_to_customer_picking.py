from datetime import datetime, timedelta, timezone

from odoo import fields, models


class PickingToCustomerWizard(models.AbstractModel):
    _name = "abstract.to.customer.wizard"
    _description = "Abstract class for wizards to send a device after a rental or order"

    # To be overriden:
    entity_id = fields.Many2one("crm.lead", string="Lead", required=True)

    usage = fields.Selection(related="entity_id.contract_id.stock_ownership")

    scheduled_date = fields.Datetime(
        string="Scheduled date",
        help="Defaults to today + 4 days at 3pm",
        required=True,
        default=lambda self: (
            fields.Datetime.context_timestamp(
                self.env.user, datetime.now() + timedelta(days=4)
            )
            .replace(hour=15, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        ),
    )

    products = fields.Many2many(
        "product.product",
        string="Products to send",
        required=True,
        domain=[("product_tmpl_id.type", "=", "product")],
        default=lambda self: self._compute_default_product_ids(),
    )

    carrier_account_id = fields.Many2one(
        "carrier.account",
        string="Carrier account",
        default=lambda self: self._compute_default_carrier_account(),
    )

    comment = fields.Text(help="You can add a comment for the preparation team here")

    def _get_related_entity(self, allow_use_default=True):
        entity = self.entity_id
        model_name = self._fields["entity_id"].comodel_name
        if allow_use_default and not entity and "default_entity_id" in self.env.context:
            entity = self.env[model_name].browse(self.env.context["default_entity_id"])
        return entity

    def _compute_default_product_ids(self):
        services = self._get_related_entity(allow_use_default=True).mapped(
            "contract_id.contract_line_ids.sale_order_line_id.product_id"
        )
        default_products = services.mapped("primary_storable_variant_id")
        default_products |= services.mapped("secondary_storable_variant_ids")
        return default_products

    def _compute_default_carrier_account(self):
        return self._get_related_entity()._delivery_tracking_parent().carrier_account_id

    def create_picking(self):
        related_entity = self._get_related_entity()
        tracking_parent_entity = related_entity._delivery_tracking_parent()
        contract = related_entity.contract_id

        picking = contract.ask_picking(
            origin=self.entity_id,
            scheduled_date=self.scheduled_date,
            products=self.products,
            carrier_account=self.carrier_account_id,
            comment=self.comment,
            picking_type=tracking_parent_entity.picking_type_id,
        )

        # Link created picking to the initial sale
        if contract.stock_ownership == "customer":
            so = contract.mapped("contract_line_ids.sale_order_line_id.order_id")
            so.picking_ids |= picking
            # Also try to link moves and sale lines:
            so_lines = so.order_line
            for move in picking.move_ids:
                so_line = so_lines.filtered(lambda ol: ol.product_id == move.product_id)
                if so_line:
                    move.sale_line_id = so_line[0]

        return picking


class CrmLeadPickingToCustomerWizard(models.TransientModel):
    _name = "crm.lead.to.customer.wizard"
    _inherit = "abstract.to.customer.wizard"
    _description = "Create a picking from a lead right after a rental sale"

    entity_id = fields.Many2one("crm.lead", string="Lead", required=True)
    os = fields.Selection(
        [
            ("none", "No OS"),
            ("android", "Android standard"),
            ("eos", "e/OS/"),
            ("windows", "Windows"),
            ("ubuntu", "Ubuntu"),
        ],
        string="Operating system",
        required=True,
    )


class ProjectTaskPickingToCustomerWizard(models.TransientModel):
    _name = "project.task.to.customer.wizard"
    _inherit = "abstract.to.customer.wizard"
    _description = "Create a picking from a task right after a sale with services order"

    entity_id = fields.Many2one("project.task", string="Task", required=True)
