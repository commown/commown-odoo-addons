from markupsafe import Markup

from odoo import _, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_origin_thread_link_element(self):
        return (
            "<a target='_blank' href='%(domain)s/web?model=%(model)s&id=%(res_id)s' class=''>#%(res_id)s</a>"
            % {
                "domain": self.env.ref("website.default_website").domain,
                "model": self._name,
                "res_id": self.id,
            }
        )

    def message_post(
        self, *args, body="", subject=None, email_from=None, author_id=None, **kwargs
    ):
        res = super().message_post(
            *args,
            body=body,
            subject=subject,
            email_from=email_from,
            author_id=author_id,
            **kwargs,
        )
        if res.message_type in ("email", "comment") and res:
            origin_thread_link = _("(from %s)", self._get_origin_thread_link_element())
            channel_body = Markup(origin_thread_link + "<br/><br/>") + body

            redirects = self.env["mail.thread.redirect"].search(
                [("model_name", "=", self._name)]
            )
            for redirect in redirects:
                if self.filtered_domain(redirect._get_eval_domain()):
                    redirect.target_channel_id.message_post(
                        body=channel_body,
                        message_type="comment",
                        subtype_xml="mail.mt_comment",
                    )

        return res
