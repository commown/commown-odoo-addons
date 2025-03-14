from odoo import _

SLIMPAY_ERROR_CODES = {
    "AC01": _("Account Identifier incorrect"),
    "AC04": _("Account closed"),
    "AC06": _("Account blocked"),
    "AC13": _("Debtor account is a consumer account"),
    "AG01": _("Direct Debit forbidden on this account for regulatory reasons"),
    "AG02": _(
        "Operation code/transaction code/sequence type incorrect, invalid file format"
    ),
    "AM04": _("Insufficient funds"),
    "AM05": _("Duplicate collection"),
    "BE05": _("Identifier of the Creditor Incorrect"),
    "CNOR": _("Creditor Bank is not registered under this BIC in the CSM"),
    "DNOR": _("Debtor Bank is not registered under this BIC in the CSM"),
    "FF01": _("File format incomplete or invalid"),
    "FOCR": _("Following a cancellation request (by the creditor)"),
    "MD01": _("No mandate or Unauthorised Transaction"),
    "MD02": _("Mandate data missing or incorrect"),
    "MD06": _("Disputed authorised transaction"),
    "MD07": _("Debtor Deceased"),
    "MS02": _("Refusal by the Debtor"),
    "MS03": _("Reason not specified"),
    "RC01": _("Bank Identifier (BIC) Incorrect"),
    "RR01": _("Regulatory Reason"),
    "RR02": _("Regulatory Reason"),
    "RR03": _("Regulatory Reason"),
    "RR04": _("Regulatory Reason"),
    "SL01": _("Specific Service offered by the Debtor Bank"),
}
