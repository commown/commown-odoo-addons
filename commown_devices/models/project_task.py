from odoo import _, api, fields, models
from odoo.exceptions import Warning

CHECK_CONTRACT_QUANT_NB_STAGE_XML_IDS = [
    "commown_devices.diagnostic_stage",
    "commown_devices.resiliated_stage",
]

STOCK_XML_ID = "stock.stock_location_stock"


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    check_picking_assigned = fields.Boolean(
        "Check picking assigned when entering stage?",
        default=False,
    )


class ProjectTask(models.Model):
    _inherit = "project.task"

    storable_product_id = fields.Many2one(
        string="Article",
        comodel_name="product.product",
        domain=lambda self: self._compute_storable_product_domain(),
    )

    lot_id = fields.Many2one(
        string="Device",
        comodel_name="stock.production.lot",
        domain=lambda self: self._compute_lot_domain(),
    )

    device_tracking = fields.Boolean(
        "Use for device tracking?", related="project_id.device_tracking"
    )

    def _compute_storable_product_domain(self):
        domain = [("type", "=", "product")]
        if self.require_contract:
            products = self._may_be_related_lots().mapped("product_id")
            domain = [("id", "in", products.ids)]
        return domain

    def _may_be_related_lots(self):
        """Return lots that lay be related to current task:
        - those already in charge of the partner (contract.quant_ids)
        - those sent to the partner but not arrived yet.
        """
        lots = self.env["stock.production.lot"]
        contracts = self.env["contract.contract"]

        if self.contract_id:
            contracts = self.contract_id

        elif self.commercial_partner_id:
            domain = [
                ("partner_id.commercial_partner_id", "=", self.commercial_partner_id.id)
            ]
            contracts = contracts.search(domain)

        for contract in contracts:
            lots |= contract.quant_ids.mapped("lot_id")
            lots |= contract.picking_ids.filtered(
                lambda c: c.state == "assigned"
            ).mapped("move_line_ids.lot_id")

        return lots

    def _compute_lot_domain(self):
        domain = []

        product = self.storable_product_id
        if product:
            domain.append(("product_id", "=", product.id))

        if self.require_contract:
            lots = self._may_be_related_lots()
            domain.append(("id", "in", lots.ids or [0]))

        else:
            qdom = [
                ("quantity", ">", 0),
                "|",
                (
                    "location_id",
                    "child_of",
                    self.env.ref("commown_devices.stock_location_devices_to_check").id,
                ),
                (
                    "location_id",
                    "child_of",
                    self.env.ref("commown_devices.stock_location_new_devices").id,
                ),
            ]
            if product:  # optimize the request a bit
                qdom.append(("lot_id.product_id", "=", product.id))
            quants = self.env["stock.quant"].search(qdom)
            domain.append(("id", "in", quants.mapped("lot_id").ids))

        return domain

    def _reset_field_target(self, field_name, domain):
        """Set value of `field_name` according to its `domain` and actual value

        Perform a search of the possible values from `domain` and:
        - if there is a single possible value, use it to set the field
        - otherwise, if the actual value isn't one of them, reset the field
        - otherwise do nothing (and let the actual value)
        """

        model = self.env[self._fields[field_name].comodel_name]
        possible_values = model.search(domain)
        if len(possible_values) == 1:
            setattr(self, field_name, possible_values)
        else:
            value = getattr(self, field_name)
            if value and value not in possible_values:
                setattr(self, field_name, False)

    @api.onchange("partner_id")
    def onchange_partner_id_restrict_storable_product_and_lot_id(self):
        "If contract_id could not be guessed, restrict product and lot at best"
        if not self.contract_id:  # otherwise another onchange will do the job
            return self.onchange_contract_or_product()

    @api.onchange("contract_id", "storable_product_id")
    def onchange_contract_or_product(self):
        lot_domain = self._compute_lot_domain()
        product_domain = self._compute_storable_product_domain()

        self._reset_field_target("lot_id", lot_domain)
        self._reset_field_target("storable_product_id", product_domain)

        return {
            "domain": {
                "lot_id": lot_domain,
                "storable_product_id": product_domain,
            }
        }

    @api.onchange("lot_id")
    def onchange_lot_id(self):
        if self.lot_id:
            self.storable_product_id = self.lot_id.product_id
            if not self.contract_id:
                contracts = (
                    self.lot_id.mapped("quant_ids")
                    .filtered(lambda q: q.quantity > 0)
                    .mapped("contract_id")
                )
                if len(contracts) == 1:
                    self.contract_id = contracts.id

    @api.constrains("stage_id")
    def onchange_stage_id_prevent_contract_resiliation_with_device(self):
        check_stage_ids = tuple(
            self.env.ref(ref).id for ref in CHECK_CONTRACT_QUANT_NB_STAGE_XML_IDS
        )
        erroneous_task = self.search(
            [
                ("id", "in", self.ids),
                ("contract_id.quant_nb", ">", 0),
                ("stage_id", "in", check_stage_ids),
            ]
        )
        if erroneous_task:
            raise Warning(
                _(
                    "These tasks can not be moved forward. There are still device(s) "
                    "associated with their contract: %s"
                )
                % erroneous_task.ids
            )

    @api.constrains("stage_id")
    def onchange_stage_id_check_assigned_picking(self):
        stock_location = self.env.ref(STOCK_XML_ID)
        erroneous_task = self.search(
            [
                ("id", "in", self.ids),
                ("stage_id.check_picking_assigned", "=", True),
            ]
        ).filtered(
            lambda task: not any(
                [
                    picking["origin"] == task.get_name_for_origin()
                    and picking.state == "assigned"
                    and "/" + str(stock_location.id) + "/"
                    in picking.location_id.parent_path
                    for picking in task.contract_id.picking_ids
                ]
            )
        )
        if erroneous_task:
            raise Warning(
                _(
                    "These tasks can not be moved forward. There are no picking "
                    "linked to those tasks: %s"
                )
                % erroneous_task.ids
            )

    def action_scrap_device(self):
        scrap_loc = self.env.ref("stock.stock_location_scrapped")

        ctx = {
            "default_product_id": self.lot_id.product_id.id,
            "default_lot_id": self.lot_id.id,
            "default_origin": self.get_name_for_origin(),
            "default_scrap_location_id": scrap_loc.id,
        }

        current_loc = (
            self.env["stock.quant"]
            .search(
                [
                    ("lot_id", "=", self.lot_id.id),
                    ("quantity", ">", 0),
                ]
            )
            .location_id
        )
        if current_loc:
            ctx["default_location_id"] = current_loc[0].id

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.scrap",
            "name": _("Scrap device"),
            "view_mode": "form",
            "view_type": "form",
            "context": ctx,
        }

    def action_move_involved_product(self):
        """Choose the right picking creation wizard depending
        on product tracking mode
        """
        if self.storable_product_id.tracking == "serial":
            wizard = "project.task.involved_device_picking.wizard"
        else:
            wizard = "project.task.involved_nonserial_product_picking.wizard"

        return {
            "type": "ir.actions.act_window",
            "res_model": wizard,
            "name": _("Move involved product"),
            "view_mode": "form",
            "view_type": "form",
            "target": "new",
            "context": {"default_task_id": self.id},
        }

    def get_name_for_origin(self):
        return "Task-%s" % self.id
