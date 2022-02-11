from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


class DeviceAsAServiceTC(RentalSaleOrderTC):

    def setUp(self):
        super(DeviceAsAServiceTC, self).setUp()

        partner = self.env.ref('base.partner_demo_portal')
        tax = self.get_default_tax()
        contract_tmpl = self._create_rental_contract_tmpl(
            1, contract_line_ids=[
                self._contract_line(1, '1 month Fairphone premium', tax),
                self._contract_line(1, 'Accessory: ##ACCESSORY##', tax),
                ])
        self.storable_product = self.env['product.template'].create({
            'name': 'Fairphone 3', 'type': 'product', 'tracking': 'serial',
        })
        team = self.env.ref('sales_team.salesteam_website_sales')

        sold_product = self._create_rental_product(
            name='Fairphone as a Service',
            list_price=60., rental_price=30.,
            property_contract_template_id=contract_tmpl.id,
            storable_product_id=self.storable_product.id,
            followup_sales_team_id=team.id,
        )

        assert sold_product.is_contract  # XXX requires cache invalidation

        oline = self._oline(sold_product, product_uom_qty=3)
        self.so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [oline],
        })
        self.so.action_confirm()

        self.location_fp3_new = self.env["stock.location"].create({
            "name": "New FP3 devices",
            "usage": "internal",
            "partner_id": 1,
            "location_id": self.env.ref("commown_devices"
                                        ".stock_location_new_devices").id,
        })

    def adjust_stock(self, product=None, qty=1., serial='serial-0',
                     location=None, date="2000-01-01"):
        if product is None:
            product = self.storable_product.product_variant_id
        lot = self.env['stock.production.lot'].create({
            'name': serial,
            'product_id': product.id,
        })
        location = location or self.location_fp3_new

        inventory = self.env["stock.inventory"].create({
            "name": "test stock %s" % serial,
            "location_id": location.id,
            "filter": "lot",
            "lot_id": lot.id,
        })
        inventory.action_start()
        inventory.line_ids |= self.env["stock.inventory.line"].create({
            "product_id": lot.product_id.id,
            "location_id": location.id,
            "prod_lot_id": lot.id,
            "product_qty": 1,
        })
        inventory.action_validate()
        assert inventory.state == "done", (
            "Unexpected inventory state %s" % inventory.state)

        assert lot.quant_ids
        self.env.cr.execute(
            "UPDATE stock_quant SET in_date=%(date)s WHERE id in %(ids)s",
            {"date": date, "ids": tuple(lot.quant_ids.ids)})
        self.env.cache.invalidate()

        return lot

    def send_device(self, serial, contract=None, date=None):
        contract = contract or self.so.order_line.contract_id
        quant = self.env["stock.quant"].search([
            ("lot_id.name", "=", serial),
            ("quantity", ">", 0),
        ])
        contract.send_device(quant, date, True)


class WizardPickingTC(DeviceAsAServiceTC):

    def prepare_wizard(self, entity, entity_field, user_choices=None):
        wizard_name = "%s.picking.wizard" % entity._name
        wizard_model = self.env[wizard_name].with_context({
            "default_%s" % entity_field: entity.id,
            "active_model": entity._name,
            "active_id": entity.id,
            "active_ids": entity.ids,
        })

        # Get default values
        fields = wizard_model.fields_get()
        defaults = wizard_model.default_get(fields.keys())
        choices = defaults.copy()
        if user_choices is None:
            user_choices = {}
        choices.update(user_choices)

        # Execute onchange methods
        domains = {name: field.get("domain", None)
                   for name, field in fields.items()}
        specs = wizard_model._onchange_spec()
        result = wizard_model.onchange(
            choices, list(user_choices.keys()), specs)
        updates = result.get("value", {})
        for name, val in updates.items():
            if isinstance(val, tuple):
                updates[name] = val[0]
        choices.update(updates)

        # Apply domain restrictions
        for name, domain in result.get("domain", {}).items():
            domains[name] = domain
        possible_values = {}
        for name, field in fields.items():
            domain = domains[name]
            if isinstance(domain, str):
                context = choices.copy()
                # Remove builtins from eval context: "id" can be used in domains
                context["__builtins__"] = {}
                try:
                    domain = eval(domain, context)
                except:
                    domain = None
            if domain is None:
                continue
            possible_values[name] = self.env[field["relation"]].search(domain)
        return defaults, possible_values
