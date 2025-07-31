from odoo import _, models
from odoo.exceptions import UserError


class UtmMergeRemoveUtilsMixin(models.AbstractModel):
    _name = "utm.merge_remove.mixin"
    _description = "Mixin for utm classes, to easily merge/ safely remove them"

    def _related_entities_by_field(self):
        fields = self.env["ir.model.fields"].search([("relation", "=", self._name)])

        for field in fields:
            model = field.model_id.model
            if model == "utm.mixin":
                continue
            yield field, self.env[model].search([(field.name, "in", self.ids)])

    def action_merge(self):
        "Merge current sources, making related entities point to the first one"
        keep_id = self.ids[0]
        to_remove = self.browse(self.ids[1:])

        for field, entities in to_remove._related_entities_by_field():
            entities.update({field.name: keep_id})

        to_remove.sudo().unlink()

    def action_remove(self):
        """Remove current sources if they are not related to any entity
        and raise a user error otherwise.
        """
        for field, entities in self._related_entities_by_field():
            if entities:
                raise UserError(
                    _("Cannot remove: %(nb_ent)d '%(field)s' point to '%(ent_names)s'")
                    % {
                        "nb_ent": len(entities),
                        "field": field.model_id.name,
                        "ent_names": ",".join(entities.mapped(field.name + ".name")),
                    }
                )
        else:
            self.sudo().unlink()


class UtmSource(models.Model):
    _name = "utm.source"
    _inherit = ["utm.source", "utm.merge_remove.mixin"]


class UtmCampaign(models.Model):
    _name = "utm.campaign"
    _inherit = ["utm.campaign", "utm.merge_remove.mixin"]
