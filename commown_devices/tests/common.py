import json
from datetime import date

from lxml import etree

from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


def create_config(serv_tmpl, storable_type, stor_tmpl, stor_variant, att_val_ids=None):
    attrs = {
        "service_tmpl_id": serv_tmpl.id,
        "storable_type": storable_type,
        "storable_tmpl_id": stor_tmpl.id,
        "storable_variant_id": stor_variant.id,
    }
    if att_val_ids:
        attrs["attribute_value_ids"] = [(6, 0, att_val_ids.ids)]

    return serv_tmpl.env["product.service_storable_config"].create(attrs)


def add_attributes_to_product(product, attribute, attribute_values):
    product.env["product.template.attribute.line"].create(
        {
            "product_tmpl_id": product.id,
            "attribute_id": attribute.id,
            "value_ids": [(6, 0, attribute_values.ids)],
        }
    )


class BaseLotTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_tmpl = cls.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
            }
        )
        cls.product = cls.product_tmpl.product_variant_id
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "test-lot",
                "product_id": cls.product.id,
            }
        )
        cls.location_available_for_rent = cls.env.ref(
            "commown_devices.stock_location_available_for_rent"
        )
        cls.location_internal_available = cls.env["stock.location"].create(
            {
                "name": "Test internal available location",
                "usage": "internal",
                "partner_id": 1,
                "location_id": cls.location_available_for_rent.id,
            }
        )

        cls.quant = cls.env["stock.quant"].create(
            {
                "product_id": cls.lot.product_id.id,
                "lot_id": cls.lot.id,
                "location_id": cls.location_internal_available.id,
                "quantity": 1,
            }
        )


class DeviceAsAServiceTC(RentalSaleOrderTC):
    confirm_sale = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        partner = cls.env.ref("base.partner_demo_portal")
        tax = cls.get_default_tax()
        contract_tmpl = cls._create_rental_contract_tmpl(
            1,
            contract_line_ids=[
                cls._contract_line(1, "1 month ##PRODUCT##", tax),
                cls._contract_line(1, "Accessory: ##ACCESSORY##", tax),
            ],
        )
        cls.storable_product = cls.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
            }
        )
        team = cls.env.ref("sales_team.salesteam_website_sales")

        cls.service_product = cls._create_rental_product(
            name="Fairphone as a Service",
            list_price=60.0,
            recurrent_payment_amount=30.0,
            property_contract_template_id=contract_tmpl.id,
            primary_storable_variant_id=cls.storable_product.product_variant_id.id,
            followup_sales_team_id=team.id,
        )

        assert cls.service_product.is_contract  # XXX requires cache invalidation

        oline = cls._oline(cls.service_product, product_uom_qty=3)
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [oline],
            }
        )
        if cls.confirm_sale:
            cls.so.action_confirm()

        cls.env.flush_all()

        cls.location_fp3_new = cls.env["stock.location"].create(
            {
                "name": "New FP3 devices",
                "usage": "internal",
                "partner_id": 1,
                "location_id": cls.env.ref(
                    "commown_devices.stock_location_new_devices"
                ).id,
            }
        )

    @classmethod
    def adjust_stock(
        cls,
        product=None,
        qty=1.0,
        serial="serial-0",
        location=None,
        date="2000-01-01",
        grade_lot=True,
    ):
        if product is None:
            product = cls.storable_product.product_variant_id
        grade = cls.env.ref("commown_grade.grade_A0")
        lot = cls.env["stock.lot"].create(
            {
                "name": serial,
                "product_id": product.id,
                "grade_id": grade_lot and grade.id,
            }
        )
        location = location or cls.location_fp3_new

        quant = cls.env["stock.quant"].create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "lot_id": lot.id,
                "inventory_quantity": qty,
            }
        )
        quant.action_apply_inventory()
        # I think it should not be done as i makes quant dates incoherent with moves
        # quant.update({"in_date": date, "inventory_date": date})

        assert quant.quantity == qty
        assert lot.quant_ids

        return lot

    @classmethod
    def adjust_stock_notracking(cls, product, location, qty=1.0, date="2000-01-01"):
        quant = cls.env["stock.quant"].create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "inventory_quantity": qty,
            }
        )
        quant.action_apply_inventory()

        # quant.in_date = dateutil.parser.parse(date)

        return product

    @classmethod
    def send_device(cls, serial, contract=None, date=None, location=None):
        contract = contract or cls.so.order_line.contract_id
        lot = cls.env["stock.lot"].search([("name", "=", serial)])
        contract.send_devices(
            lot.ensure_one(), {}, send_lots_from=location, date=date, do_transfer=True
        )

    def prepare_ui(
        self, created_model_name, related_entity, relation_field, user_choices=None
    ):
        created_model = self.env[created_model_name].with_context(
            **{
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
                context["uid"] = self.env.user.id
                # Remove builtins from eval context: "id" can be used in domains
                context["__builtins__"] = {}
                try:
                    domain = safe_eval(domain, context)
                except Exception:
                    domain = []
            if domain is None:
                continue
            possible_values[name] = self.env[field["relation"]].search(domain.copy())

        # Apply view domains:
        tree = etree.fromstring(created_model.get_view()["arch"])
        for view_field in tree.xpath("//field[@domain]"):
            name = view_field.get("name")
            values["uid"] = self.env.user.id
            try:
                domain = safe_eval(view_field.get("domain"), values)
            except Exception:
                domain = []
            if isinstance(domain, str):  # the domain was a field itself
                domain = json.loads(domain)
            try:
                possible_values[name] = self.env[fields[name]["relation"]].search(
                    domain.copy()
                )
            except KeyError:
                continue

        return values, possible_values


def create_lot_and_quant(env, lot_name, product, location):
    # XXX Duplicate of adjust stock
    lot = env["stock.lot"].create(
        {
            "name": lot_name,
            "product_id": product.id,
            "grade_id": env.ref("commown_grade.grade_A0").id,
        }
    )

    env["stock.quant"].create(
        {
            "product_id": product.id,
            "lot_id": lot.id,
            "location_id": location.id,
            "quantity": 1,
        }
    )
    return lot


class BaseWizardToEmployeeMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project = cls.env["project.project"].create({"name": "Test"})
        partner = cls.env["res.partner"].create(
            {
                "firstname": "Firsttest",
                "lastname": "Lasttest",
                "street": "8A rue Schertz",
                "zip": "67200",
                "city": "Strasbourg",
                "country_id": cls.env.ref("base.fr").id,
                "email": "contact@commown.coop",
                "mobile": "0601020304",
                "parent_id": 1,
            }
        )

        cls.task = cls.env["project.task"].create(
            {"name": "test", "project_id": project.id, "partner_id": partner.id}
        )
        cls.carrier_account = cls.env.ref(
            "commown_shipping.carrier-account-colissimo-std-account"
        )
        cls.carrier = cls.env.ref("delivery_roulier_laposte_fr.delivery_carrier_DOS")
        cls.carrier.carrier_account_id = cls.carrier_account

    def get_wizard(self, **kwargs):
        kwargs.setdefault("task_id", self.task.id)
        kwargs.setdefault("delivered_by_hand", False)
        return self.env["project.task.to.employee.wizard"].create(kwargs)


class BaseToCustomerPickingWizardTC(DeviceAsAServiceTC):
    "Base class to write identical tests for picking to customer from leads and tasks"

    confirm_sale = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        service_template = cls.service_product.product_tmpl_id
        cls.usbc_cable = cls.env["product.template"].create(
            {
                "name": "Test USB-C Cable",
                "type": "product",
                "tracking": "none",
            }
        )
        cls.protective_screen = cls.env["product.template"].create(
            {
                "name": "Protective Screen",
                "type": "product",
                "tracking": "none",
            }
        )
        cls.loc_new_untracked = cls.env.ref(
            "commown_devices.stock_location_modules_and_accessories"
        )
        cls.adjust_stock_notracking(
            cls.usbc_cable.product_variant_id, cls.loc_new_untracked
        )
        # We don't ajdust stock of protective screen because lack of stock case is
        # tested
        cls.attribute_usbc = cls.env["product.attribute"].create(
            {"name": "Send Cable ?", "create_variant": "always"}
        )
        cls.attribute_color = cls.env.ref("product.product_attribute_2")
        color_values = cls.env["product.attribute.value"].search(
            [("attribute_id.id", "=", cls.attribute_color.id)]
        )
        usbc_values = cls.env["product.attribute.value"].create(
            [
                {"attribute_id": cls.attribute_usbc.id, "name": "Yes"},
                {"attribute_id": cls.attribute_usbc.id, "name": "No"},
            ]
        )
        add_attributes_to_product(
            service_template,
            cls.attribute_color,
            color_values,
        )
        add_attributes_to_product(
            cls.storable_product,
            cls.attribute_color,
            color_values,
        )
        add_attributes_to_product(
            service_template,
            cls.attribute_usbc,
            usbc_values,
        )
        cls.color1 = color_values[0]
        with_usbc = usbc_values.filtered(lambda v: v.name == "Yes")
        cls.fp3_plus_storable_color1 = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", cls.storable_product.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.color1.id,
                ),
            ]
        )
        create_config(
            service_template,
            "primary",
            cls.storable_product,
            cls.fp3_plus_storable_color1,
            att_val_ids=cls.color1,
        )
        create_config(
            service_template,
            "secondary",
            cls.protective_screen,
            cls.protective_screen.product_variant_id,
        )
        create_config(
            service_template,
            "secondary",
            cls.usbc_cable,
            cls.usbc_cable.product_variant_id,
            att_val_ids=with_usbc,
        )
        cls.fp3_plus_service_color1_with_usb = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", service_template.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.color1.id,
                ),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    with_usbc.id,
                ),
            ]
        )
        cls.so.order_line[0].product_id = cls.fp3_plus_service_color1_with_usb

    def prepare_wizard(self, related_entity, relation_field, user_choices=None):
        wizard_name = "%s.to.customer.wizard" % related_entity._name
        return self.prepare_ui(
            wizard_name, related_entity, relation_field, user_choices=user_choices
        )


class LinkWizardTC(DeviceAsAServiceTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env.ref("base.res_partner_3")
        cls.previous_po_of_supplier = cls.env["purchase.order"].search(
            [
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    cls.supplier.commercial_partner_id.id,
                )
            ]
        )

        cls.fp = cls.env.ref("product_rental.prod_fp")
        cls.pc1, cls.pc2 = cls.env.ref("product_rental.prod_pc").product_variant_ids

        date_po = date(2021, 1, 1)

        oline1 = cls._oline(cls.fp, product_qty=3, date_planned=date_po)
        oline2 = cls._oline(cls.pc1, product_qty=5, date_planned=date_po)
        oline3 = cls._oline(cls.pc2, product_qty=8, date_planned=date_po)
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.supplier.id,
                "order_line": [oline1, oline2, oline3],
            }
        )

    def prepare_wizard(self, base_name, rel_entity, relation_field, user_choices=None):
        wizard_name = "%s.link.wizard" % base_name
        return self.prepare_ui(
            wizard_name, rel_entity, relation_field, user_choices=user_choices
        )
