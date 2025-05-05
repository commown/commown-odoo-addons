from odoo import fields, models


class TestPaymentProvider(
    models.Model
):  # pylint: disable=consider-merging-classes-inherited
    _inherit = "payment.provider"
    _description = "Test payment.provider model"

    code = fields.Selection(
        selection_add=[("test", "Test")], ondelete={"test": "set default"}
    )


class TestPaymentTransaction(
    models.Model
):  # pylint: disable=consider-merging-classes-inherited
    _inherit = "payment.transaction"
    _description = "Test payment.transaction model"

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_id.code == "test":
            if notification_data["simulated_state"] == "pending":
                self._set_pending()
            elif notification_data["simulated_state"] == "done":  # pragma: no cover
                self._set_done()
        return
