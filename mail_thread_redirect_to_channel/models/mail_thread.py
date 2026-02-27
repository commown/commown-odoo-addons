from markupsafe import Markup

from odoo import _, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_origin_thread_link_element(self):
        # Return a link to the given model, as an internal link (no domain)
        return (
            "<a target='_blank' href='/web#model=%(model)s&id=%(res_id)s' class=''>#%(res_id)s</a>"
            % {
                "model": self._name,
                "res_id": self.id,
            }
        )

    def message_post(self, *args, body="", **kwargs):
        res = super().message_post(*args, body=body, **kwargs)
        if res.message_type in ("email", "comment") and res:
            origin_thread_link = _("(from %s)", self._get_origin_thread_link_element())
            channel_body = Markup(origin_thread_link + "<br/><br/>") + body

            redirects = self.env["mail.thread.redirect"].search(
                [("model_name", "=", self._name)]
            )
            for redirect in redirects:
                if (
                    not redirect.only_portal_users
                    or res.author_id.user_ids.has_group("base.group_portal")
                ) and self.filtered_domain(redirect._get_eval_domain()):
                    redirect.target_channel_id.message_post(
                        body=channel_body,
                        message_type="comment",
                        subtype_xml="mail.mt_comment",
                    )

        return res
