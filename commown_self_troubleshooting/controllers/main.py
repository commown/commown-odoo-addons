import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SelfHelp(http.Controller):

    action_tags = {"inform": ["tag-inform-only"]}

    def ref(self, suffix):
        return request.env.ref("commown_self_troubleshooting." + suffix)

    def _description(self, **post):
        return self.ref(post["issue-description-template"]).render(post)

    def _tag_ids(self, **post):
        ids = [self.ref(t).id for t in self.action_tags.get(post["action"], ())]
        ids.append(self.ref("tag-self-troubleshooting").id)
        names = post.get("tags", "").split(",")
        if names:
            ids.extend(request.env["project.tags"].search([("name", "in", names)]).ids)
        if post.get("screwdriver", None) == "yes":
            ids.append(self.ref("tag-need-screwdriver").id)
        return ids

    def _check_posted_contract_id(self, contract_id):
        contract_id = int(contract_id)
        contract = request.env["contract.contract"].sudo().browse(contract_id)
        partner = request.env.user.partner_id
        if contract.partner_id.commercial_partner_id != partner.commercial_partner_id:
            _logger.warning(
                "partner %d posted self_troubleshooting data for contract %d"
                " which is not his",
                partner.id,
                contract.id,
            )
            raise ValueError("Invalid contract")
        return contract_id

    @http.route(["/self-troubleshoot"], type="http", auth="user", website=True)
    def create_support_card(self, **kw):
        _logger.info("create_support_card called with parameters %s", kw)
        env = request.env
        partner = env.user.partner_id
        post = request.params.copy()

        project = env.ref(post["project_ref"])

        task_data = {
            "name": post["self-troubleshoot-type"],
            "priority": str(int(post.get("priority", 0))),
            "contractual_issue_type": post.get("contractual_issue_type"),
            "contractual_issue_date": post.get("contractual_issue_date"),
            "partner_id": partner.id,
            "description": self._description(**post),
            "project_id": project.id,
            "tag_ids": [(6, 0, self._tag_ids(**post))],
        }

        if post.get("device_contract", None):
            task_data["contract_id"] = self._check_posted_contract_id(
                post["device_contract"]
            )

        if post.get("stage_ref", None):
            stage_ref = post["stage_ref"]
            task_data["stage_id"] = env.ref(stage_ref).id

        task = env["project.task"].sudo().create(task_data)
        task.onchange_contract_or_product()

        if partner not in task.message_follower_ids.mapped("partner_id"):
            comment = env.ref("mail.mt_comment")
            rating = env.ref("project.mt_task_rating")
            env["mail.followers"].create(
                {
                    "res_model": task._name,
                    "res_id": task.id,
                    "partner_id": partner.id,
                    "subtype_ids": [(6, 0, [comment.id, rating.id])],
                }
            )

        return request.redirect("/my/task/%d" % task.id)
