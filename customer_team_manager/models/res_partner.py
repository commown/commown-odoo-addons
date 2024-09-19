from odoo import _, api, models
from odoo.exceptions import UserError

from .employee import Employee


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_create_employee(self, admin=False):
        if admin and len(self) != 1:
            raise UserError(_("Cannot create more than one admin at once!"))

        empl_model = self.env["customer_team_manager.employee"]
        already_exist = empl_model.search([("partner", "in", self.ids)])
        result = empl_model

        ref = self.env.ref
        group_customer_admin = ref("customer_team_manager.group_customer_admin")
        admin_role = ref("customer_team_manager.customer_role_admin")
        user_role = ref("customer_team_manager.customer_role_user")

        fields = ["firstname", "lastname", "email", "phone"]
        for partner in self - already_exist.mapped("partner"):
            if partner.type != "contact":
                raise UserError(
                    _("Partner '%s' (id %d) is of type '%s', not 'contact'")
                    % (partner.name, partner.id, partner.type)
                )
            if partner.is_company:
                raise UserError(
                    _("Partner '%s' (id %d) is a company") % (partner.name, partner.id)
                )
            if admin:
                if not partner.user_ids:
                    raise UserError(
                        _("Partner '%s' (id %d) has no user yet")
                        % (partner.name, partner.id)
                    )
                partner.user_ids[0].groups_id |= group_customer_admin
                role = admin_role
            else:
                role = user_role

            attrs = {field: partner[field] for field in fields}
            attrs.update(
                {
                    "roles": [(6, 0, role.ids)],
                    "partner": partner.id,
                    "company": partner.commercial_partner_id.id,
                }
            )

            result |= empl_model.create(attrs)

        def employees_decr(title, employees):
            result = [title]
            for employee in employees:
                roles = ", ".join(employee.roles.mapped("name"))
                result.append("%s (%s)" % (employee.display_name, roles))
            return result

        msg = ""
        sep = "<br>- "
        if result:
            msg += sep.join(
                employees_decr(_("<b>Created %d employees:</b>") % len(result), result)
            )
        else:
            msg += _("<b>No employee created!</b>")

        if already_exist:
            msg += "<br><br>" + sep.join(
                employees_decr(_("<b>Already existing employee(s):</b>"), already_exist)
            )

        self.env.user.notify_info(sticky=True, message=msg)

    def get_employees(self):
        empl_model = self.env["customer_team_manager.employee"]
        return empl_model.search([("partner", "in", self.ids)])

    @api.multi
    def write(self, vals):
        result = super().write(vals)

        to_sync = Employee._sync_fields_with_partner.intersection(vals)
        if to_sync and not self.env.context.get("_in_employee_res_partner_write_sync"):
            employee = (
                self.env["customer_team_manager.employee"]
                .sudo()
                .search([("partner", "=", self.id)])
            )
            employee.with_context(_in_res_partner_write_sync=True).update(
                {attr: vals[attr] for attr in to_sync}
            )

        return result
