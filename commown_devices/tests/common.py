import dateutil.parser

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


def create_config(serv_tmpl, type, stor_tmpl, stor_variant, att_val_ids=None):
    return serv_tmpl.env["product.service_storable_config"].create(
        {
            "service_tmpl_id": serv_tmpl.id,
            "storable_type": type,
            "attribute_value_ids": [(6, 0, att_val_ids.ids)]
            if att_val_ids is not None
            else False,
            "storable_tmpl_id": stor_tmpl.id,
            "storable_variant_id": stor_variant.id,
        }
    )


def add_attributes_to_product(product, attribute, attribute_values):
    line = product.env["product.template.attribute.line"].create(
        {
            "product_tmpl_id": product.id,
            "attribute_id": attribute.id,
            "value_ids": [(6, 0, attribute_values.ids)],
        }
    )


class DeviceAsAServiceTC(RentalSaleOrderTC):
    def setUp(self):
        super(DeviceAsAServiceTC, self).setUp()

        partner = self.env.ref("base.partner_demo_portal")
        tax = self.get_default_tax()
        contract_tmpl = self._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                self._contract_line(1, "1 month ##PRODUCT##", tax),
                self._contract_line(1, "Accessory: ##ACCESSORY##", tax),
            ],
        )
        self.storable_product = self.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
            }
        )
        team = self.env.ref("sales_team.salesteam_website_sales")

        sold_product = self._create_rental_product(
            name="Fairphone as a Service",
            list_price=60.0,
            rental_price=30.0,
            property_contract_template_id=contract_tmpl.id,
            storable_product_id=self.storable_product.id,
            followup_sales_team_id=team.id,
        )

        assert sold_product.is_contract  # XXX requires cache invalidation

        oline = self._oline(sold_product, product_uom_qty=3)
        self.so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [oline],
            }
        )
        self.so.action_confirm()

        self.location_fp3_new = self.env["stock.location"].create(
            {
                "name": "New FP3 devices",
                "usage": "internal",
                "partner_id": 1,
                "location_id": self.env.ref(
                    "commown_devices.stock_location_new_devices"
                ).id,
            }
        )

    def adjust_stock(
        self, product=None, qty=1.0, serial="serial-0", location=None, date="2000-01-01"
    ):
        if product is None:
            product = self.storable_product.product_variant_id
        lot = self.env["stock.production.lot"].create(
            {
                "name": serial,
                "product_id": product.id,
            }
        )
        location = location or self.location_fp3_new

        inventory = self.env["stock.inventory"].create(
            {
                "name": "test stock %s" % serial,
                "location_id": location.id,
                "filter": "lot",
                "lot_id": lot.id,
            }
        )
        inventory.action_start()
        inventory.line_ids |= self.env["stock.inventory.line"].create(
            {
                "product_id": lot.product_id.id,
                "location_id": location.id,
                "prod_lot_id": lot.id,
                "product_qty": 1,
            }
        )
        inventory.action_validate()
        assert inventory.state == "done", (
            "Unexpected inventory state %s" % inventory.state
        )

        assert lot.quant_ids
        self.env.cr.execute(
            "UPDATE stock_quant SET in_date=%(date)s WHERE id in %(ids)s",
            {"date": date, "ids": tuple(lot.quant_ids.ids)},
        )
        self.env.cache.invalidate()

        return lot

    def adjust_stock_notracking(self, product, location, qty=1.0, date="2000-01-01"):

        inventory = self.env["stock.inventory"].create(
            {
                "name": "test stock %s" % product.name,
                "location_id": location.id,
                "filter": "product",
                "product_id": product.id,
                "date": dateutil.parser.parse(date),
            }
        )
        inventory.action_start()
        inventory.line_ids |= self.env["stock.inventory.line"].create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "product_qty": qty,
            }
        )
        inventory.action_validate()
        assert inventory.state == "done", (
            "Unexpected inventory state %s" % inventory.state
        )

        self.env.cache.invalidate()
        quant = self.env["stock.quant"].search(
            [("product_id.id", "=", product.id), ("location_id.id", "=", location.id)]
        )
        quant.in_date = dateutil.parser.parse(date)

        return product

    def send_device(self, serial, contract=None, date=None):
        contract = contract or self.so.order_line.contract_id
        quant = self.env["stock.quant"].search(
            [
                ("lot_id.name", "=", serial),
                ("quantity", ">", 0),
            ]
        )
        contract.send_device(quant, date=date, do_transfer=True)

    def prepare_ui(
        self, created_model_name, related_entity, relation_field, user_choices=None
    ):
        created_model = self.env[created_model_name].with_context(
            {
                "default_%s" % relation_field: related_entity.id,
                "active_model": related_entity._name,
                "active_id": related_entity.id,
                "active_ids": related_entity.ids,
            }
        )

        # Get default values
        fields = created_model.fields_get()
        defaults = created_model.default_get(fields.keys())
        values = defaults.copy()
        if user_choices is None:
            user_choices = {}
        values.update(user_choices)

        # Execute onchange methods
        specs = created_model._onchange_spec()
        result = created_model.onchange(values, list(user_choices.keys()), specs)
        updates = result.get("value", {})
        for name, val in updates.items():
            if isinstance(val, tuple):
                updates[name] = val[0]
        values.update(updates)

        # Apply domain restrictions
        domains = {name: field.get("domain", None) for name, field in fields.items()}
        for name, domain in result.get("domain", {}).items():
            domains[name] = domain
        possible_values = {}
        for name, field in fields.items():
            domain = domains[name]
            if isinstance(domain, str):
                context = values.copy()
                # Remove builtins from eval context: "id" can be used in domains
                context["__builtins__"] = {}
                try:
                    domain = eval(domain, context)
                except:  # noqa: E722
                    domain = []
            if domain is None:
                continue
            possible_values[name] = self.env[field["relation"]].search(domain)
        return values, possible_values
