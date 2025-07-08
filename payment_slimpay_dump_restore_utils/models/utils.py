import json
import logging
import os.path as osp

from odoo.exceptions import MissingError

from odoo.addons.account_payment_slimpay.models import slimpay_utils

_logger = logging.getLogger(__name__)


# Low level helpers ###########################################################


def mandate_doc_ref(provider, mandate_doc):
    "Return the reference of the mandate supplied as an HAPI representation"
    return (mandate_doc["reference"], mandate_doc["id"])


def get_partner(provider, mandate_doc):
    client = provider.slimpay_client()
    subscriber_url = mandate_doc[client.method_name("get-subscriber")].url
    pid = subscriber_url.rsplit("/", 1)[-1]
    partner_model = provider.env["res.partner"]
    if pid.isdigit():
        partner = partner_model.browse(int(pid))
    else:
        partner = provider.env["res.partner"].search(
            [
                ("payment_token_id.provider_ref", "=", mandate_doc["id"]),
            ]
        )
        if len(partner) > 1:
            pid = client.get(subscriber_url)["reference"]
            partner = partner_model.browse(int(pid))
    return partner


def mandate_doc_to_repr(provider, mandate_doc):
    """Return a json representation of the supplied HAPI mandate doc that
    is suitable for creating a copy using the `create-mandates` HAPI call.
    """
    partner = get_partner(provider, mandate_doc)
    bank_account_doc = provider.slimpay_client().action(
        "GET", "get-bank-account", doc=mandate_doc
    )
    if partner:
        signatory = slimpay_utils.subscriber_from_partner(partner)["signatory"]
        signatory["bankAccount"] = {
            "bic": bank_account_doc["bic"],
            "iban": bank_account_doc["iban"],
        }
        return {
            "reference": mandate_doc["reference"],
            "dateSigned": mandate_doc["dateSigned"],
            "createSequenceType": "FRST",
            "subscriber": {"reference": partner.id},
            "signatory": signatory,
        }
    return {}


def get_all_mandates_repr(provider, transformer_func, **params):
    """Query Slimpay API's `provider` account for all mandates with
    optional search criteria `params` and return them after applying
    the given transformer function.
    """
    client = provider.slimpay_client()
    params["creditorReference"] = provider.slimpay_creditor
    _logger.debug("Fetching first mandates...")
    doc = client.action("GET", "search-mandates", params=params)
    if "mandates" in doc:
        for mandate_doc in doc["mandates"]:
            result = transformer_func(provider, mandate_doc)
            if result:
                yield result
        page_num = doc["page"]["totalPages"]
        for page in range(1, page_num):
            _logger.debug("Fetching page %d / %d...", page + 1, page_num)
            doc = client.get(doc.links["next"].url)
            for mandate_doc in doc["mandates"]:
                result = transformer_func(provider, mandate_doc)
                if result:
                    yield result


def set_mandate(provider, partner, mandate_id):
    partner.payment_token_id.update(
        {
            "provider_ref": mandate_id,
            "provider_id": provider.id,
        }
    )


def replace_mandate(provider, mandate_repr):
    """Replace partner's mandate by a new one described by `mandate_repr`
    in the context of given `provider`.
    """
    partner = (
        provider.env["res.partner"]
        .browse(mandate_repr["subscriber"]["reference"])
        .ensure_one()
    )
    # Fix wrong data for companies and missing country
    if partner.is_company:
        mandate_repr["signatory"]["givenName"] = "-"
    if mandate_repr["signatory"]["billingAddress"]["country"] is None:
        _logger.debug(
            "WARNING! No country set for %s. Assuming FR. Please fix data.",
            partner.name,
        )
        mandate_repr["signatory"]["billingAddress"]["country"] = "FR"

    # Remove BIC, which may be wrong (for unknown reason, CMCIFR2AXXX
    # crashes) and can be computed automatically by Slimpay from the IBAN
    mandate_repr["signatory"]["bankAccount"].pop("bic", None)

    mandate_repr["creditor"] = {"reference": provider.slimpay_creditor}
    new_mandate_doc = provider.slimpay_client().action(
        "POST", "create-mandates", params=mandate_repr
    )
    set_mandate(provider, partner, new_mandate_doc["id"])
    _logger.debug(
        "Created new mandate %s for %s", new_mandate_doc["reference"], partner.name
    )


# High level helpers ##########################################################


def dump_all_mandates(provider, refresh, mandates_fpath, **params):
    """Extract all mandates and dump them as a json descr in `mandates_fpath`
    If the `refresh` parameter is True (the default), try to read given file
    for a previous mandate list and only append newly signed mandates.
    """

    old_mandates = []

    if refresh and osp.isfile(mandates_fpath):
        with open(mandates_fpath) as fobj:
            old_mandates = json.load(fobj)
            if old_mandates:
                params["dateSignedAfter"] = max(m["dateSigned"] for m in old_mandates)

    mandates = old_mandates + list(
        get_all_mandates_repr(provider, mandate_doc_to_repr, **params)
    )
    json.dump(mandates, open(mandates_fpath, "w"))


def filter_has_contract(provider, mandate_repr):
    "mandate partner has no contract"
    partner = provider.env["res.partner"].browse(
        mandate_repr["subscriber"]["reference"]
    )
    return bool(
        provider.env["contract.contract"].search(
            [
                ("commercial_partner_id", "=", partner.commercial_partner_id.id),
            ]
        )
    )


def restore_all_missing_mandates(
    provider,
    mandates_fpath="/tmp/mandates.json",
    filter_func=filter_has_contract,
    **params,
):
    "Restore all mandates from production to preproduction environment"

    mandates_repr = json.load(open(mandates_fpath))
    known_mandate_refs = dict(
        get_all_mandates_repr(provider, mandate_doc_ref, **params)
    )
    for mandate_repr in mandates_repr:
        partner = (
            provider.env["res.partner"]
            .browse(mandate_repr["subscriber"]["reference"])
            .exists()
        )
        if not partner:
            _logger.error(
                "Partner %s of mandate %s not found in odoo (name: %s).",
                mandate_repr["subscriber"]["reference"],
                mandate_repr["reference"],
                (
                    mandate_repr["signatory"]["givenName"]
                    + mandate_repr["signatory"]["familyName"]
                ),
            )
            continue
        if filter_func and not filter_func(provider, mandate_repr):
            _logger.info(
                "Skipping mandate %s of %s: %s",
                mandate_repr["reference"],
                partner.name,
                filter_func.__doc__,
            )
            continue
        ref = mandate_repr["reference"] = "TEST" + mandate_repr["reference"][4:]
        if ref not in known_mandate_refs:
            try:
                replace_mandate(provider, mandate_repr)
            except MissingError:
                _logger.error(
                    "Partner not found when trying to replace mandate for %s"
                    % mandate_repr["signatory"]["email"]
                )
                continue
            except Exception:
                import traceback as tb

                _logger.error(
                    "Error when trying to replace mandate for %s:\n%s",
                    mandate_repr["signatory"]["email"],
                    tb.format_exc(),
                )
                continue
            mandate_repr_ = next(
                get_all_mandates_repr(provider, mandate_doc_ref, mandateReference=ref)
            )
            known_mandate_refs[ref] = mandate_repr_
        else:
            set_mandate(provider, partner, known_mandate_refs[ref])
            _logger.debug("Pre-existing mandate %s assigned to %s", ref, partner.name)
