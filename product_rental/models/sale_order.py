import logging
from collections import defaultdict

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

    def contractual_documents(self, allow_from_template=False):
        """Return the contractual docs of the products' contract template

        These are the docs attached to the contract template filtered according
        to the partner's language, if set (otherwise they are all returned):
        - docs without a language set are returned
        - docs with the same language as the partner are returned
        """
        self.ensure_one()

        contracts = self.env["contract.contract"].of_sale(self)
        if contracts or not allow_from_template:
            docs = {c: c.contractual_documents for c in contracts}
        else:
            cts = self.mapped("order_line.product_id.property_contract_template_id")
            docs = {ct: ct.contractual_documents for ct in cts}

        if self.partner_id.lang:
            _logger.debug(
                "Partner %s (%d) lang is %s. Restricting contractual documents"
                " to those without a language set or set to the partner's.",
                self.partner_id.name,
                self.partner_id.id,
                self.partner_id.lang,
            )
            docs = {
                k: v.filtered(lambda d: d.lang in (False, self.partner_id.lang))
                for k, v in docs.items()
            }

        return docs

    # pylint: disable=missing-return
    @api.depends("order_line.product_uom_qty", "order_line.product_id")
    def _compute_cart_info(self):
        """In Commown activities we can have services that required a shipped product"""
        super()._compute_cart_info()
        for order in self:
            order.only_services = all(
                (
                    not line.product_id.has_recurrent_payment  # we need to ship the product
                    and line.product_id.type in ("service", "digital")
                )
                for line in order.website_order_line
            )

    def action_quotation_send(self):
        "Add contractual documents to the quotation email"
        self.ensure_one()
        email_act = super().action_quotation_send()
        order_attachments = self.env["ir.attachment"]
        for atts in self.contractual_documents(allow_from_template=True).values():
            order_attachments |= atts
        if order_attachments:
            _logger.info(
                "Prepare sending %s with %d attachment(s): %s",
                self.name,
                len(order_attachments),
                ", ".join(["'%s'" % n for n in order_attachments.mapped("name")]),
            )
            ids = [
                att.id for att in sorted(order_attachments, key=lambda att: att.name)
            ]
            email_act["context"].setdefault("default_attachment_ids", []).append(
                (6, 0, ids)
            )
        return email_act

    def assign_contract_products(self):
        "Assign main product and accessories to n contracts per sale order line"

        bought_accessories = defaultdict(list)
        for line in self.order_line:
            accessory = line.product_id
            if accessory.has_recurrent_payment and not accessory.is_contract:
                bought_accessories[line.product_id] += int(line.product_uom_qty) * [
                    line
                ]
        _logger.debug(
            "%s: bought %d accessories",
            self.name,
            sum(len(line) for line in bought_accessories.values()),
        )

        contract_descrs = [
            {"so_line": so_line, "main": so_line.product_id, "accessories": []}
            for so_line in self.order_line.filtered("product_id.is_contract")
            for num in range(int(so_line.product_uom_qty))
        ]

        for contract_num, contract_descr in enumerate(contract_descrs, 1):
            _logger.debug(
                "Examining so_line %s (contract %d)",
                contract_descr["so_line"].name,
                contract_num,
            )

            _logger.debug(
                "Unassigned accessories: %s",
                ", ".join(
                    "%s (x%d)" % (a.name, len(so_lines))
                    for (a, so_lines) in bought_accessories.items()
                ),
            )

            main_product = contract_descr["main"]
            main_accessories = (
                main_product.accessory_product_ids
                | main_product.optional_product_ids.mapped("product_variant_ids")
            )

            for accessory, so_lines in list(bought_accessories.items()):
                if accessory in main_accessories:
                    contract_descr["accessories"].append((accessory, so_lines.pop(0)))
                    _logger.debug("> Assigned accessory %s", accessory.name)
                    if len(bought_accessories[accessory]) == 0:
                        del bought_accessories[accessory]

        _logger.debug(
            "Accessories to be assigned to last contract (%d): %s",
            len(contract_descrs),
            ", ".join(
                "%s (x%d)" % (a.name, len(so_lines))
                for (a, so_lines) in bought_accessories.items()
            )
            or "None",
        )

        if contract_descrs:
            for accessory, so_lines in bought_accessories.items():
                contract_descrs[-1]["accessories"].extend(
                    [(accessory, so_line) for so_line in so_lines]
                )

        _logger.info(
            "Contracts to be created for %s:\n%s",
            self.name,
            "\n".join(
                "%d/ %s: %s"
                % (
                    n,
                    c["main"].name,
                    ", ".join(
                        "%s (SO line %d)" % (product.name, so_line.id)
                        for (product, so_line) in c["accessories"]
                    ),
                )
                for n, c in enumerate(contract_descrs, 1)
            ),
        )

        return contract_descrs

    def _add_analytic_account(self, contract):
        """Create an analytic account with the same name and partner as the
        given contract and attach it to the contract.
        """
        company = contract.company_id
        aa = self.env["account.analytic.account"].create(
            {
                "name": contract.name,
                "company_id": company.id,
                "partner_id": contract.partner_id.id,
                "plan_id": company.analytic_plan_id.id,
            }
        )
        contract.group_id = aa

    def action_create_contract(self):
        contracts = self.env["contract.contract"]
        contract_descrs = self.assign_contract_products()

        for count, contract_descr in enumerate(contract_descrs, 1):
            contract_template = (
                contract_descr["main"]
                .with_company(self.company_id)
                .property_contract_template_id
            )

            values = self._prepare_contract_value(contract_template)
            values["name"] = "%s-%02d" % (self.name, count)

            env = self.with_context(contract_descr=contract_descr).env
            contract = env["contract.contract"].create(values)
            contract._onchange_contract_template_id()
            contract._onchange_contract_type()
            contract._compute_date_end()

            self._add_analytic_account(contract)

            contracts |= contract

        return contracts
