from datetime import date, timedelta

from odoo.addons.contract.tests.test_contract import TestContractBase


def is_mail(message):
    return list(message.subtype_id.get_external_id().values())[0] == "mail.mt_comment"


def get_model(obj):
    return obj.env["ir.model"].search([("model", "=", obj._name)])


def reply_message(reference_message_id, email, new_message_id, body_text):
    return f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <{ new_message_id }>
References: { reference_message_id }
Subject: sale team 1 in company 1
From:  { email }
To: catchall@yourcompany.com
Content-Type: multipart/alternative; boundary="0000000000000000000000000001"

--0000000000000000000000000001
Content-Type: text/plain; charset="UTF-8"

{ body_text }

--0000000000000000000000000001
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>{ body_text }</div>

--0000000000000000000000000001--
"""


class ContractTemplateMailGenerator(TestContractBase):
    def create_mt(self, **kwargs):
        return self.env["mail.template"].create(
            {
                "model_id": kwargs.get("model_id", get_model(self.contract).id),
                "name": kwargs.get("name", "Test template name"),
                "subject": kwargs.get("subject", "${object.name}"),
                "body_html": kwargs.get("body_html", "Test body"),
            }
        )

    def create_contract(self, date_start, date_end=None, **kwargs):
        kwargs.setdefault("contract_template_id", self.template.id)
        contract = self.contract.copy(kwargs)
        contract.date_start = date_start
        if date_end:
            contract.date_end = date_end
        contract._flush()  # Push date_start compute to DB
        return contract

    def create_gen(self, interval_number, text="Test body", **kwargs):
        values = {
            "contract_id": self.template.id,
            "mail_template_id": self.create_mt(body_html=text).id,
            "interval_number": interval_number,
            "interval_type": "daily",
        }
        values.update(kwargs)
        pmg = self.env["contract_emails.planned_mail_generator"].create(values)
        # Force stored fields storage:
        pmg._compute_send_date_offset_days()
        pmg._flush()
        return pmg

    def test_cron(self):
        "Emails planned in the past must be sent"
        pmt_model = self.env["contract_emails.planned_mail_generator"]
        self.env.ref("contract_emails.channel")

        self.create_gen(0, text="Mail at contract start", max_delay_days=10)
        self.create_gen(6, text="Mail after 6 days", max_delay_days=10)
        self.create_gen(25, text="Mail after 25 days", max_delay_days=10)

        today = date.today()
        t_30 = today - timedelta(days=30)

        c1 = self.create_contract(today)
        c2 = self.create_contract(today - timedelta(days=7))
        c3 = self.create_contract(t_30)
        c4 = self.create_contract(t_30, date_end=today)
        c5 = self.create_contract(t_30, dont_send_planned_mails=True)

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

        # Channel must be notified when customer recipient answers:
        c1_msg = c1.message_ids[0]
        self.assertIn("Mail at contract start", c1_msg.body)

        chan = self.env.ref("contract_emails.channel")

        message = reply_message(
            c1_msg.message_id,
            c1.partner_id.email,
            "Message-ID-1",
            "Very happy to be a Commowner!",
        )

        old_msgs = chan.message_ids
        result = self.env["mail.thread"].message_process(None, message)

        # Check the References header is correct
        self.assertEqual(result, c1.id)

        # Check the message was forwarded:
        new_msgs = chan.message_ids - old_msgs
        self.assertEqual(len(new_msgs), 1)
        self.assertIn("Very happy to be a Commowner!", new_msgs.body)
        mails[c1] |= new_msgs.parent_id

        # Check messages are not sent again and again
        pmt_model.cron_send_planned_mails()

        for c in c1 | c2 | c3:
            self.assertEqual(c.message_ids.filtered(is_mail), mails[c])

        message2 = reply_message(
            c1_msg.message_id,
            self.env.ref("base.user_demo").email,
            "Message-ID-2",
            "My pleasure :-)",
        )

        old_msgs = chan.message_ids
        result2 = self.env["mail.thread"].message_process(None, message2)

        # Check the References header is correct
        self.assertEqual(result2, c1.id)

        # Check the message was NOT forwarded:
        self.assertEqual(chan.message_ids, old_msgs)
