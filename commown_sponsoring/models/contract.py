from datetime import date, datetime, timedelta

from odoo import models

DEFAULT_DELTA_WEEKS_CONTRACT_START = 6


class SponsoringContract(models.Model):
    _inherit = "contract.contract"

    def write(self, values):
        "Create sponsors on newly started contracts"
        res = super().write(values)

        if "date_start" in values:
            param_delta_length = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "commown_sponsoring.delta_weeks_contract_start",
                    DEFAULT_DELTA_WEEKS_CONTRACT_START,
                )
            )
            for contract in self:
                if contract.date_start < date.today() + timedelta(
                    weeks=param_delta_length
                ):
                    contract.partner_id._create_sponsor_campaign()

        return res

    def _cron_send_sponsor_notif_emails(self):
        cron = self.env.ref(
            "commown_sponsoring.cron_send_sponsorship_notification_mail"
        )
        now = datetime.now()
        withdrawal_period_buffer = timedelta(
            days=int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("product_rental.rental_withdrawal_period_days", "0")
            )
        )

        # Due to an issue for comparing fields of type 'Date' and 'Datetime' (or timestamp),
        # especially around the truncating of the hours in the datetime,
        # we directly query in SQL using the timestamp converter on the Date field.
        query = """
        SELECT id
        FROM contract_contract
        WHERE
            date_start::timestamp < %s
            AND (
                (date_end IS NULL AND recurring_next_date IS NOT NULL)
                OR date_end < %s
            )
        """
        query_args = [now - withdrawal_period_buffer, now]
        if cron.lastcall:
            query += " AND date_start::timestamp >= %s"
            query_args.append(cron.lastcall - withdrawal_period_buffer)
        self.env.cr.execute(query, query_args)
        contract_ids = [res[0] for res in self.env.cr.fetchall()]
        contracts = self.env["contract.contract"].browse(contract_ids)

        found_sponsors = {}
        for contract in contracts:
            # If a sponsor code was used on the related order,
            # notify the sponsoring partner their code was used and by whom.
            order_coupons = contract.mapped(
                "contract_line_ids.sale_order_line_id.order_id.used_coupon_ids"
            )

            sponsor = order_coupons.campaign_id.sponsor_partner_id
            if sponsor:
                found_sponsors.setdefault(sponsor, self.env["contract.contract"])
                found_sponsors[sponsor] |= contract

        mail_tmpl = self.env.ref("commown_sponsoring.mail_sponsoring_notify")
        for sponsor, contracts in found_sponsors.items():
            sponsor.with_context(sponsored=contracts).message_post_with_template(
                mail_tmpl.id,
                message_type="comment",
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
