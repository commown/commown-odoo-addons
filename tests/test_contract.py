from datetime import date, timedelta

from .common import ContractPlannedMailBaseTC


class ContractTemplateMailGenerator(ContractPlannedMailBaseTC):

    def create_contract(self, date, template, **kwargs):
        kwargs["recurring_next_date"] = date
        kwargs["contract_template_id"] = template.id
        kwargs["date_start"] = date
        return self.contract.copy(kwargs)

    def create_gen(self, interval_number):
        return self.env['contract_emails.planned_mail_generator'].create({
            "contract_id": self.template.id,
            "mail_template_id": self.create_mt(body_html=u"Test").id,
            "interval_number": interval_number,
            "interval_type": "monthly",
        })

    def assertContractPmtDatesEqual(self, dates_by_contract_id):
        pmts = self.env["contract_emails.planned_mail_template"].search([
            ("res_id", "in", dates_by_contract_id.keys()),
        ])
        self.assertEqual(
            sorted([(pmt.res_id, pmt.planned_send_date) for pmt in pmts]),
            sorted([(c_id, date)
                    for c_id, dates in dates_by_contract_id.items()
                    for date in dates
            ])
        )

    def test_create_and_write(self):
        """ Creating a contract from a template with generators creates planned
        emails. Updating the contract start date updates their send date.
        """
        self.create_gen(0)
        self.create_gen(6)
        c1 = self.create_contract("2050-09-15", self.template)
        c2 = self.create_contract("2051-01-03", self.template)

        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15", "2051-03-15"],
            c2.id: ["2051-01-03", "2051-07-03"],
        })

        c1.write({"date_start": "2050-05-03"})
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-05-03", "2050-11-03"],
            c2.id: ["2051-01-03", "2051-07-03"],
        })

        pmts = c1._get_planned_emails()
        self.assertTrue(pmts.exists())
        c1.unlink()
        self.assertFalse(pmts.exists())

        self.assertEqual(len(c2._get_planned_emails()), 2)
        c2.write({'date_start': date.today() - timedelta(days=90)})
        self.assertEqual(len(c2._get_planned_emails()), 1)

    def test_set_contract_date_end(self):
        """ When a contract end date is updated, handle related planned mails
        - if unset while it was set: regenerate mails to send after old end date
        - if set while it was unset: remove planned mails after the end date
        - if moved later: regenerate mails to send between old and new dates
        - if moved sooner: remove planned mails after the new end date
        """
        self.create_gen(0)
        self.create_gen(6)
        c1 = self.create_contract("2050-09-15", self.template)
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15", "2051-03-15"],
        })

        # End date from unset to set
        c1.write({"date_end": "2051-01-02"})
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15"],
        })

        # End date set later
        # Make sure existing pmt was not removed and regenerated
        older_pmt_id = c1._get_planned_emails().id
        c1.write({"date_end": "2051-04-01"})
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15", "2051-03-15"],
        })
        self.assertIn(older_pmt_id, c1._get_planned_emails().ids)

        # End date set sooner
        c1.write({"date_end": "2051-01-02"})
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15"],
        })
        self.assertEqual(older_pmt_id, c1._get_planned_emails().id)

        # End date unset
        c1.write({"date_end": False})
        self.assertContractPmtDatesEqual({
            c1.id: ["2050-09-15", "2051-03-15"],
        })
        self.assertIn(older_pmt_id, c1._get_planned_emails().ids)
