from odoo import _, api, fields, models


class OriginDocumentMixin(models.AbstractModel):
    _name = "origin_document.mixin"
    _description = "Mixin to add an origin document to any model"

    origin_document_model = fields.Char("Origin document model", readonly=True)
    origin_document_id = fields.Integer("Origin document ID", readonly=True)
    origin_document_name = fields.Char(
        compute="_compute_origin_document_name",
        store=False,
    )
    origin_document_model_name = fields.Char(
        compute="_compute_origin_document_name",
        store=False,
    )

    @api.depends("origin_document_id", "origin_document_model")
    def _compute_origin_document_name(self):
        for record in self:
            doc = record.origin_document()
            if doc:
                doc_model = self.env["ir.model"].search([("model", "=", doc._name)])
                record.origin_document_name = doc.display_name
                record.origin_document_model_name = doc_model.name
            else:
                record.origin_document_name = False
                record.origin_document_model_name = False

    def origin_document(self):
        self.ensure_one()
        if self.origin_document_model and self.origin_document_id:
            return (
                self.env[self.origin_document_model]
                .browse(self.origin_document_id)
                .exists()
            )

    def action_open_origin_document(self):
        origin_document = self.origin_document()
        if origin_document:
            return {
                "name": _("Origin document"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": origin_document._name,
                "res_id": origin_document.id,
                "target": "current",
            }
