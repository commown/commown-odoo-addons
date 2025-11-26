from odoo.tests import TransactionCase


class CommownShippingTaskActionsTC(TransactionCase):
    """
    Check "Print label" action presence in project.task form view.
    Base attributes can be overriden to apply to other record types.
    """

    obj_ref = "project.project_1_task_1"
    view_ref = "project.view_task_form2"
    action_name = "[commown] SUPPORT,GESTION: print label"

    def isActionInFormView(self, form_view):
        return any(
            action["name"] == self.action_name
            for action in form_view["views"]["form"]["toolbar"]["action"]
        )

    def test_print_label_action(self):
        """
        Only users with the dedicated print label group
        should be able to access the print label action
        """
        # Setup
        user = self.env.ref("base.user_demo")
        label_group = self.env.ref("commown_shipping.group_print_label")

        obj_w_user = self.env.ref(self.obj_ref).with_user(user)
        view = self.env.ref(self.view_ref)

        # Case 1: User is not in print label group
        self.assertNotIn(label_group, user.groups_id)

        view_case_1 = obj_w_user.get_views([(view.id, "form")], {"toolbar": True})
        self.assertFalse(self.isActionInFormView(view_case_1))

        # Case 2: User is in print label group
        user.groups_id |= label_group

        view_case_2 = obj_w_user.get_views([(view.id, "form")], {"toolbar": True})
        self.assertTrue(self.isActionInFormView(view_case_2))


class CommownShippingLeadActionsTC(CommownShippingTaskActionsTC):
    """
    Checks action presence in crm.lead form view,
    by running same test_print_label_action but with a crm.lead record.
    """

    obj_ref = "crm.crm_case_1"
    view_ref = "crm.crm_lead_view_form"
    action_name = "[commown] Print label"
