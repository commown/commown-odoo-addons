from odoo.addons.contract.tests.test_contract import TestContractBase


def is_mail(message):
    return message.subtype_id.get_xml_id().values()[0] == "mail.mt_comment"


def get_model(object):
    return object.env['ir.model'].search([("model", "=", object._name)])


class ContractPlannedMailBaseTC(TestContractBase):

    def create_mt(self, **kwargs):
        return self.env["mail.template"].create({
            "model_id": kwargs.get("model_id", get_model(self.contract).id),
            "name": kwargs.get("name", "Test template"),
            "subject": kwargs.get("subject", "${object.name}"),
            "body_html": kwargs.get("body_html", u"Test"),
            "user_signature": False,
        })
