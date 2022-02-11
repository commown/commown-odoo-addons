from odoo import fields, models, api


class Contract(models.Model):
    _inherit = "contract.contract"

    main_contract_line_id = fields.Many2one(
        "contract.line",
        string="Main contract line",
        help="Contract line of the main rental product",
        compute="_compute_main_contract_line",
        store=True,
        readonly=True,
    )

    min_contract_duration = fields.Integer(
        string='Min contract duration',
        help='Minimum contract duration in recurring interval unit',
        related='main_contract_line_id.commitment_duration',
        store=True,
        readonly=True,
    )

    min_contract_end_date = fields.Date(
        string='Min contract end date',
        related='main_contract_line_id.commitment_end_date',
        store=True,
        readonly=True,
    )

    date_start = fields.Date(
        string='Start date',
        compute="_compute_date_start",
        store=False,
        inverse="_inverse_date_start",
    )

    @api.depends("contract_line_ids")
    def _compute_main_contract_line(self):
        for contract in self:
            main_line = contract.contract_line_ids.filtered(
                "sale_order_line_id.product_id.product_tmpl_id"
                ".property_contract_template_id")
            if len(main_line) == 1:
                contract.main_contract_line_id = main_line.id
            else:
                contract.main_contract_line_id = False

    def _init_main_contract_line(self):
        "Use this once after v12 installation, then removed me"
        secondary_names = (
            "remise", "windows", "clavier", "open os",
            "batterie supplémentaire", "power pack")
        for contract in self:
            main_line = contract.contract_line_ids.filtered(
                "sale_order_line_id.product_id.product_tmpl_id"
                ".property_contract_template_id")
            if main_line:
                contract.main_contract_line_id = main_line[0].id
                # Only 3 prints... may be removed
                if len(main_line) > 1 and len(main_line.filtered(lambda l: (
                        "Remise" not in l.product_id.name
                        and l.qty_type == "fixed"))) > 1:
                    print("More than one: %s" % contract.name)
            elif len(contract.contract_line_ids) == 1:
                contract.main_contract_line_id = contract.contract_line_ids[0]
            else:
                other_candidates = contract.contract_line_ids.filtered(
                    lambda l: not any(sn in l.name.lower()
                                      for sn in secondary_names))
                if len(other_candidates) == 1:
                    contract.main_contract_line_id = other_candidates
                else:
                    print("No main contract line for %s" % contract.name)
                    contract.main_contract_line_id = False

    @api.depends("main_contract_line_id.date_start")
    def _compute_date_start(self):
        for contract in self:
            contract.date_start = contract.main_contract_line_id.date_start

    def _inverse_date_start(self):
        for contract in self:
            contract.main_contract_line_id.date_start = contract.date_start

    @api.model
    def of_sale(self, sale):
        return self.search([
            ("contract_line_ids.sale_order_line_id.order_id", "=", sale.id),
        ])
