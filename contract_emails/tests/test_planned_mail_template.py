from datetime import datetime, timedelta

from odoo import fields

from .common import ContractPlannedMailBaseTC, is_mail


class PlannedMailTemplateTC(ContractPlannedMailBaseTC):

    def plan_mail(self, mt_id, res_id=None, **_timedelta):
        date = datetime.now() + timedelta(**_timedelta)
        return self.env["contract_emails.planned_mail_template"].create({
            "mail_template_id": mt_id,
            "res_id": res_id or self.contract.id,
            "planned_send_date": date.strftime(fields.DATETIME_FORMAT),
        })

    def test_cron(self):
        """ Planned emails not already sent nor in the future must be posted """
        # Following must be posted:
        pmts = self.env['contract_emails.planned_mail_template']
        pmts |= self.plan_mail(self.create_mt(body_html=u"Test 1").id, days=-3)
        pmts |= self.plan_mail(self.create_mt(body_html=u"Test 2").id, days=-2)
        pmts |= self.plan_mail(self.create_mt(body_html=u"Test 3").id, days=-1)
        # While following must not:
        self.plan_mail(self.create_mt(body_html=u"Test 4").id, days=10)
        pm = self.plan_mail(self.create_mt(body_html=u"Test 5").id, days=-10)
        pm.effective_send_time = (datetime.now() - timedelta(days=10)).strftime(
            fields.DATETIME_FORMAT)
        # Execute cron and check
        self.env[
            "contract_emails.planned_mail_template"].cron_send_planned_mails()
        contract_emails = self.contract.message_ids.filtered(is_mail)
        self.assertEqual(len(contract_emails), 3)
        self.assertEqual(contract_emails.mapped('body'),
                         [u"<p>Test 3</p>", u"<p>Test 2</p>", u"<p>Test 1</p>"])
        self.assertTrue(any(pmts.mapped('effective_send_time')))

    def test_name(self):
        self.contract.name = u"My contract"
        pmt = self.plan_mail(
            self.create_mt(name=u"My template", body_html=u"Test").id, days=0)
        self.assertEqual(pmt.display_name,
                         u"My contract - Agrolait - My template")
