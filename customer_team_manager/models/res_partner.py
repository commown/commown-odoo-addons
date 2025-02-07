from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    ALLOWED_CUSTOMER_ADMIN_ATTRS = frozenset(
        {
            "name",
            "firstname",
            "lastname",
            "email",
            "phone",
            "team",
            "customer_note",
            "customer_roles",
            "image_medium",
            "active",
            "__last_update",
        }
    )

    AUTHORIZED_ACTIONS = {
        "customer_team_manager.action_wizard_portal_access",
    }

    team = fields.Many2one(
        "customer_team_manager.team",
        index=True,
        ondelete="restrict",
        domain="[('customer_company', '=', commercial_partner_id)]",
        groups=",".join(
            (
                "sales_team.group_sale_manager",
                "customer_team_manager.group_customer_admin",
            )
        ),
    )

    parent_id = fields.Many2one(
        default=lambda self: self._compute_default_parent_id(),
    )

    customer_roles = fields.Many2many(
        "customer_team_manager.customer_role",
        string="Customer role(s)",
    )

    portal_status = fields.Selection(
        [
            ("not_granted", "Not granted"),
            ("never_connected", "Never connected"),
            ("already_connected", "Already connected"),
        ],
        default="not_granted",
        string="Portal status",
        compute="_compute_portal_status",
        store=False,
    )

    customer_note = fields.Html(
        help="You may need to take some notes, you can do that here"
    )

    def _current_user_is_customer_admin(self):
        "A lot of exagerated precautions here as the use case is perm checking"
        return (
            not self.env.user.has_group("base.group_user")
            and self.env.user.has_group("base.group_portal")
            and self.env.user.has_group("customer_team_manager.group_customer_admin")
            and self.env.user.commercial_partner_id.is_company
        )

    def _compute_default_parent_id(self):
        if self._current_user_is_customer_admin():
            return self.env.user.commercial_partner_id.id

    def _compute_portal_status(self):
        for partner in self:
            result = "not_granted"

            users = partner.sudo().user_ids
            if users:
                user = users[0]
                if user.active and user.has_group("base.group_portal"):
                    if user.state == "active":
                        result = "already_connected"
                    else:
                        result = "never_connected"

            partner.portal_status = result

    @api.model
    def fields_view_get(self, *args, **kwargs):
        "Empty the action menu -but Duplicate- when user is a customer admin"
        result = super().fields_view_get(*args, **kwargs)
        if self._current_user_is_customer_admin() and "toolbar" in result:
            actions = [
                action
                for action in result["toolbar"]["action"]
                if action.get("xml_id") in self.AUTHORIZED_ACTIONS
            ]
            result["toolbar"].update({"action": actions, "relate": []})
        return result

    @api.multi
    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        "Filter copied data to allowed attributes when user is a customer admin"

        result = super().copy_data(default=default)
        if self._current_user_is_customer_admin():
            allowed_attrs = self.ALLOWED_CUSTOMER_ADMIN_ATTRS
            for attrs in result or ():
                for attr in list(attrs):
                    if attr not in allowed_attrs:
                        attrs.pop(attr, None)
        return result

    def _check_customer_allowed_attrs(self, vals):
        """Sanitize create/ update attributes if current user is a customer admin.

        Return in this case, false otherwise.
        Raises AccessError if vals had not allowed attributes.
        """
        allowed = set(self.ALLOWED_CUSTOMER_ADMIN_ATTRS)

        if vals.get("parent_id", False) == self.env.user.commercial_partner_id.id:
            allowed.add("parent_id")

        if vals.get("company_name", True) is False:
            allowed.add("company_name")

        if set(vals) - allowed:
            raise AccessError(
                "You are not allowed to perform this operation on this partner"
            )

    @api.model
    @api.returns("self", lambda value: value.id)
    def create(self, vals):
        """Use sudo when a customer admin creates a partner, taking care of security

        There is quite a lot happening in other modules under the hood when creating a
        partner, which crashes when the user is not in base.group_user. This is why we
        need to use sudo. However
        """
        _self = self
        if self._current_user_is_customer_admin():
            vals["parent_id"] = self.env.user.commercial_partner_id.id
            self._check_customer_allowed_attrs(vals)
            _self = self.sudo()

        return super(ResPartner, _self).create(vals)

    @api.model
    def _check_one_customer_admin_at_least(self, company_partner):
        admin_group = self.env.ref("customer_team_manager.group_customer_admin")
        domain = [
            ("commercial_partner_id", "=", company_partner.id),
            ("user_ids.groups_id", "=", admin_group.id),
        ]
        if not self.sudo().search_count(domain):
            raise ValidationError(_("At least one administrator is mandatory"))

    @api.multi
    def write(self, vals):
        def is_b2c(partner):
            return not partner.commercial_partner_id.is_company

        def email_changed(partner):
            return partner.email != vals.get("email", partner.email)

        is_customer_admin = self._current_user_is_customer_admin()
        have_users = self.filtered("user_ids")

        self_sudo = self
        if is_customer_admin:
            self._check_customer_allowed_attrs(vals)
            self_sudo = self.sudo()
            if "email" in vals and have_users.filtered(email_changed):
                raise models.ValidationError(
                    _("The email of partners having portal access cannot be modified!")
                )

        # Partner deactivation makes user removal mandatory :-(
        if not vals.get("active", True) and is_customer_admin:
            self_sudo.mapped("user_ids").unlink()

        have_b2c_users = have_users.filtered(is_b2c)

        result = super(ResPartner, self_sudo).write(vals)

        # Make sure b2c users have no more customer roles
        for rec in self_sudo.filtered("customer_roles").filtered(is_b2c):
            rec.customer_roles = [(6, 0, ())]

        if "customer_roles" in vals:
            for rec in self_sudo:
                rec._reset_roles()
                if rec.commercial_partner_id.is_company:
                    self._check_one_customer_admin_at_least(rec.commercial_partner_id)

        is_the_only_company_user = self.__class__._is_the_only_company_user
        have_b2b_single_users = have_b2c_users.filtered(is_the_only_company_user)
        if have_b2b_single_users:
            all_roles = self.env["customer_team_manager.customer_role"].search([])
            have_b2b_single_users.customer_roles |= all_roles

        return result

    def _is_the_only_company_user(self):
        self.ensure_one()
        return (
            self.commercial_partner_id.is_company
            and self == self.commercial_partner_id.child_ids.filtered("user_ids")
        )

    @api.multi
    def unlink(self):
        commercial_partner = self.commercial_partner_id
        super().unlink()
        if commercial_partner.is_company:
            self._check_one_customer_admin_at_least(commercial_partner)

    @api.multi
    def action_revoke_portal_access(self):
        self.ensure_one()
        users = self.sudo().user_ids
        if users:
            users[0].groups_id -= self.env.ref("base.group_portal")
        self._reset_roles()
        self._check_one_customer_admin_at_least(self.commercial_partner_id)

    def _reset_roles(self):
        """Set the correct user groups according to partner's roles and portal access

        This is implemented in two steps:
        - remove all existing customer role groups
        - if partner has portal access, add its user its role groups
        """

        self.ensure_one()

        role_model = self.env["customer_team_manager.customer_role"]

        users = self.sudo().user_ids
        if users:
            user = users[0]
            user.groups_id -= role_model.search([]).mapped("groups")
            if user.has_group("base.group_portal"):
                user.groups_id |= self.customer_roles.mapped("groups")

    def _check_import_perms(self, values):
        "Enforce security for customer admin before using sudo on imports"
        for vals in values:
            vals["parent_id"] = self.env.user.commercial_partner_id.id
            self._check_customer_allowed_attrs(vals)

    def _load_records_create(self, values):
        "This method is used by the import UI when new records are created."

        if self._current_user_is_customer_admin():
            self._check_import_perms(values)
            return super(ResPartner, self.sudo())._load_records_create(values)
        else:
            return super()._load_records_create(values)

    def _load_records_write(self, values):
        "This method is used by the import UI when new records are updated."

        if self._current_user_is_customer_admin():
            self._check_import_perms([values])
            return super(ResPartner, self.sudo())._load_records_write(values)
        else:
            return super()._load_records_write(values)

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Users"),
                "template": "/customer_team_manager/static/xls/Commown_User_Import_Model.xlsx",
            }
        ]
