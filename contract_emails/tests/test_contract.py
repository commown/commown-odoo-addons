from datetime import date, timedelta

from odoo.addons.contract.tests.test_contract import TestContractBase


def is_mail(message):
    return list(message.subtype_id.get_xml_id().values())[0] == "mail.mt_comment"


def get_model(object):
    return object.env["ir.model"].search([("model", "=", object._name)])


class ContractTemplateMailGenerator(TestContractBase):
    def create_mt(self, **kwargs):
        return self.env["mail.template"].create(
            {
                "model_id": kwargs.get("model_id", get_model(self.contract).id),
                "name": kwargs.get("name", "Test template name"),
                "subject": kwargs.get("subject", "${object.name}"),
                "body_html": kwargs.get("body_html", "Test body"),
                "user_signature": False,
            }
        )

    def create_contract(self, date_start, date_end=None, **kwargs):
        kwargs.setdefault("contract_template_id", self.template.id)
        contract = self.contract.copy(kwargs)
        contract.contract_line_ids.update(
            {
                "recurring_next_date": date_start,
                "date_start": date_start,
            }
        )
        contract.date_start = date_start
        if date_end:
            contract.date_end = date_end
        return contract

    def create_gen(self, interval_number, text="Test body", **kwargs):
        values = {
            "contract_id": self.template.id,
            "mail_template_id": self.create_mt(body_html=text).id,
            "interval_number": interval_number,
            "interval_type": "daily",
        }
        values.update(kwargs)
        return self.env["contract_emails.planned_mail_generator"].create(values)

    def test_cron(self):
        "Emails planned in the past must be sent"
        pmt_model = self.env["contract_emails.planned_mail_generator"]
        channel = self.env.ref("contract_emails.channel")

        self.create_gen(0, text="Mail at contract start", max_delay_days=10)
        self.create_gen(6, text="Mail after 6 days", max_delay_days=10)
        g3 = self.create_gen(25, text="Mail after 25 days", max_delay_days=10)

        today = date.today()
        t_30 = today - timedelta(days=30)

        c1 = self.create_contract(today)
        c2 = self.create_contract(today - timedelta(days=7))
        c3 = self.create_contract(t_30)
        c4 = self.create_contract(t_30, date_end=today)
        c5 = self.create_contract(t_30, dont_send_planned_mails=True)

        # Check channel is not already listening to contract
        for c in c1 | c2 | c3 | c4 | c5:
            self.assertFalse(c.message_follower_ids.mapped("channel_id"))

        pmt_model.cron_send_planned_mails()

        # Mails send from contracts in emission order
        mails = {
            c: c.message_ids.filtered(is_mail).sorted("id")
            for c in (c1 | c2 | c3 | c4 | c5)
        }

        self.assertEqual(mails[c1].mapped("body"), ["<p>Mail at contract start</p>"])
        self.assertEqual(
            mails[c2].mapped("body"),
            ["<p>Mail at contract start</p>", "<p>Mail after 6 days</p>"],
        )
        self.assertEqual(
            mails[c3].mapped("body"), ["<p>Mail after 25 days</p>"]
        )  # Other mails are too old
        self.assertFalse(mails[c4])
        self.assertFalse(mails[c5])

        # Channel must follow the contracts from which an email was sent
        for c in c1 | c2 | c3:
            self.assertEqual(c.message_follower_ids.mapped("channel_id"), channel)
        for c in c4 | c5:
            self.assertFalse(c.message_follower_ids.mapped("channel_id"))

        # Check messages are not sent again and again
        pmt_model.cron_send_planned_mails()

        for c in c1 | c2 | c3:
            self.assertEqual(c.message_ids.filtered(is_mail), mails[c])

        for c in c4 | c5:
            self.assertFalse(c.message_follower_ids.mapped("channel_id"))
