from .common import ContractPlannedMailBaseTC


class ContractTemplateMailGenerator(ContractPlannedMailBaseTC):

    def create_contract(self, date, template, **kwargs):
        kwargs.setdefault("recurring_next_date", date)
        kwargs["contract_template_id"] = template.id
        contract = self.contract.copy(kwargs)
        contract.date_start = date  # avoid recurring_next_date comparison error
        return contract

    def create_gen(self, interval_number):
        return self.env['contract_emails.planned_mail_generator'].create({
            "contract_id": self.template.id,
            "mail_template_id": self.create_mt(body_html=u"Test").id,
            "interval_number": interval_number,
            "interval_type": "monthly",
        })

    def test_generator(self):
        self.create_gen(0)
        self.create_gen(6)
        c1 = self.create_contract("2020-09-15", self.template)
        c2 = self.create_contract("2021-01-03", self.template)
        self.template.generate_planned_mail_templates()

        pmts = self.env["contract_emails.planned_mail_template"].search([
            ("res_id", "in", (c1.id, c2.id)),
        ])
        self.assertEqual(
            sorted([(pmt.res_id, pmt.planned_send_date) for pmt in pmts]),
            [(c1.id, "2020-09-15"), (c1.id, "2021-03-15"),
             (c2.id, "2021-01-03"), (c2.id, "2021-07-03")]
        )
