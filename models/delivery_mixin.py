from datetime import datetime, timedelta

import lxml.etree
import requests
from iso8601 import parse_date
from odoo import _, api, fields, models
from odoo.addons.queue_job.job import job
from odoo.exceptions import UserError
from pytz import UTC

BASE_URL = "https://www.coliposte.fr/tracking-chargeur-cxf/TrackingServiceWS/track"

QUEUE_CHANNEL = "root.DELIVERY_TRACKING"

MLVARS_MAX_WAIT = timedelta(days=8)


class ParcelError(Exception):
    pass


def colissimo_status_request(login, password, ref):
    resp = requests.get(
        BASE_URL, {"accountNumber": login, "password": password, "skybillNumber": ref}
    )
    resp.raise_for_status()
    return resp.content.decode("utf-8")


class CommownTrackDeliveryMixin(models.AbstractModel):
    _name = "commown.track_delivery.mixin"

    expedition_ref = fields.Text("Expedition reference", size=64, copy=False)
    expedition_date = fields.Date("Expedition Date", copy=False)
    expedition_status = fields.Text("Expedition status", size=256, copy=False)
    expedition_status_fetch_date = fields.Datetime(
        "Expedition status fetch date", copy=False
    )
    expedition_urgency_mail_sent = fields.Boolean(
        "Expedition urgency mail send", default=False, copy=False
    )
    delivery_date = fields.Date("Delivery Date", copy=False)

    _delivery_tracking_stage_rel = "stage_id"

    # Need to be overloaded
    _delivery_tracking_parent_rel = None
    _delivery_tracking_stage_parent_rel = None

    @api.model
    def _delivery_tracking_stage_type(self):
        return self.env[self._name].fields_get("stage_id")["stage_id"]["relation"]

    @api.multi
    def _delivery_tracking_parent(self):
        return self.mapped(self._delivery_tracking_parent_rel)

    def _default_perform_actions_on_delivery(self):
        parent = self._delivery_tracking_parent()
        if not parent:
            context = self.env.context
            default_rel = "default_%s" % self._delivery_tracking_parent_rel
            if default_rel in context:
                parent = self.env[parent._name].browse(context[default_rel])
        return parent.default_perform_actions_on_delivery if parent else True

    send_email_on_delivery = fields.Boolean(
        default=_default_perform_actions_on_delivery,
        string="Automatic email on delivery",
    )
    on_delivery_email_template_id = fields.Many2one(
        "mail.template", string="Custom email model for this entity"
    )

    @api.multi
    def write(self, values):
        res = super(CommownTrackDeliveryMixin, self).write(values)
        if values.get("delivery_date", False):
            self.delivery_perform_actions()
        return res

    @api.multi
    def delivery_perform_actions(self):
        for record in self.filtered("send_email_on_delivery"):
            template = record.delivery_email_template()
            if template:
                status = record.expedition_status
                ctx = {}
                if status and status[0] == "[" and "]" in status:
                    ctx["postal_code"] = status[1 : status.find("]")]
                record.with_context(ctx).message_post_with_template(template.id)
            else:
                raise UserError(
                    _(
                        "No mail email template specified for %s"
                        " (neither in current record nor its parent)"
                    )
                    % record
                )

    @api.multi
    def delivery_email_template(self):
        """ If current entity is attached to a parent with shipping activated,
        return the entity's custom delivery mail template if any or the parent's
        delivery mail template if any. Return None if all other cases.
        """
        self.ensure_one()
        parent = self._delivery_tracking_parent()
        return (
            parent
            and parent.delivery_tracking
            and (
                self.on_delivery_email_template_id
                or parent.on_delivery_email_template_id
            )
            or None
        )

    def _delivery_tracked_records(self, marker="[colissimo: tracking]"):
        return self.env[self._name].search(
            [
                (self._delivery_tracking_stage_rel, "like", "%" + marker),
                ("expedition_ref", "!=", False),
                ("expedition_ref", "not like", "https://"),
                ("expedition_ref", "not like", "http://"),
                (
                    "%s.delivery_tracking" % self._delivery_tracking_parent_rel,
                    "=",
                    True,
                ),
            ]
        )

    def _delivery_final_stage(self, marker="[colissimo: final]"):
        self.ensure_one()
        return self.env[self._delivery_tracking_stage_type()].search(
            [
                ("name", "like", "%" + marker),
                (
                    self._delivery_tracking_stage_parent_rel,
                    "=",
                    self._delivery_tracking_parent().id,
                ),
            ]
        )

    @job(default_channel=QUEUE_CHANNEL)
    def _delivery_tracking_update(self):
        self.ensure_one()
        now = datetime.utcnow()

        infos = self._delivery_tracking_colissimo_status()
        infos.update(
            {
                "name": self.partner_id.name,
                "number": self.expedition_ref,
                "rec_model": self._name,
                "rec_id": self.id,
            }
        )
        self.update(
            {
                "expedition_status": u"[%(code)s] %(label)s" % infos,
                "expedition_status_fetch_date": now,
            }
        )

        code = infos["code"]
        date = parse_date(infos["date"])
        result = [u"%(number)s - %(name)s : %(code)s (%(label)s)" % infos]

        if code in ("LIVCFM", "LIVGAR", "LIVVOI"):
            # Parcel is considered delivered: this will trigger delivery actions
            final_stage = self._delivery_final_stage()
            if not final_stage:
                raise ValueError(u"No final stage found for %s" % self)
            self.update({"delivery_date": date.date(), "stage_id": final_stage.id})
            result.append(u"Delivered.")

        elif code.endswith("CFM") or code in (
            "DEPGUI",
            "RENARV",
            "RSTDIL",
            "RSTNCG",
            "RSTNRV",
            "RENLNA",
        ):
            # Wait!
            result.append(u"Nothing done")

        elif code in ("MLVARS", "RENAVI"):
            # More than 8 day-old MLVARS: log a warning and send an email once
            if (now.replace(tzinfo=UTC) - date) > MLVARS_MAX_WAIT:
                result.append(u"Urgency mail sent.")
                if not self.expedition_urgency_mail_sent:
                    self.expedition_urgency_mail_sent = True
                    _self = self.with_context({"postal_code": code})
                    _self.message_post_with_template(self.delivery_email_template().id)

        else:
            # Unexpected code: emit a warning
            result.append(u"Unhandled code")

        return u"\n".join(result)

    def _delivery_tracking_colissimo_status(self):
        self.ensure_one()
        account = self._delivery_tracking_parent().shipping_account_id
        resp = colissimo_status_request(
            account.login, account._get_password(), self.expedition_ref
        )
        doc = lxml.etree.fromstring(resp)
        try:
            code = doc.xpath("//eventCode/text()")[0]
            date = doc.xpath("//eventDate/text()")[0]
            label = doc.xpath("//eventLibelle/text()")[0]
        except IndexError:
            raise ParcelError(
                u"Error requesting parcel status for %s. Response was:\n%s"
                % (self, resp)
            )
        return {"code": code, "label": label, "date": date}

    @api.model
    def _cron_delivery_auto_track(self):
        records = self._delivery_tracked_records()
        for record in records:
            record.with_delay(max_retries=1)._delivery_tracking_update()
        return records


class CommownDeliveryParentMixin(models.AbstractModel):
    _name = "commown.delivery.parent.mixin"
    _inherit = "commown.shipping.parent.mixin"

    delivery_tracking = fields.Boolean("Delivery tracking", default=False)
    default_perform_actions_on_delivery = fields.Boolean(
        "By default, perform actions on delivery", default=True
    )
    on_delivery_email_template_id = fields.Many2one(
        "mail.template", string="Default delivery email model for this entity"
    )
