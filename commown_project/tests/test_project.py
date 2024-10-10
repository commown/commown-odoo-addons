from odoo.exceptions import AccessError
from odoo.tests.common import SavepointCase, tagged


@tagged("post_install", "-at_install")
class ProjectPermissionTC(SavepointCase):
    "Base class for project permissions"

    def setUp(self):
        super().setUp()

        pmanager_group = self.env.ref("project.group_project_manager")

        self.project_manager = self.env.ref("base.user_demo")

        self.user1 = self.project_manager.copy({"login": "user1", "name": "user1"})
        self.user1.groups_id -= pmanager_group
        self.user2 = self.user1.copy({"login": "user2", "name": "user2"})

        puser_group = self.env.ref("project.group_project_user")
        self.assertIn(self.user1, puser_group.users)
        self.assertIn(self.user2, puser_group.users)

        self.assertNotIn(self.user1, pmanager_group.users)
        self.assertNotIn(self.user2, pmanager_group.users)

    def create_project(self, as_user, **kwargs):
        kwargs.setdefault("user_id", as_user.id)
        return self.env["project.project"].sudo(as_user.id).create(kwargs)

    def create_task(self, as_user, **kwargs):
        return self.env["project.task"].sudo(as_user.id).create(kwargs)

    def create_task_type(self, as_user, **kwargs):
        legends = {
            "legend_normal": "normal",
            "legend_blocked": "blocked",
            "legend_done": "done",
        }
        return (
            self.env["project.task.type"].sudo(as_user.id).create({**legends, **kwargs})
        )

    def is_follower(self, user, project):
        followers = project.sudo().message_follower_ids
        return user.partner_id in followers.mapped("partner_id")

    def entity_as(self, entity, user):
        return self.env[entity._name].sudo(user.id).browse(entity.id)

    def seen_projects(self, as_user):
        return self.env["project.project"].sudo(as_user.id).search([])

    def seen_tasks(self, as_user):
        return self.env["project.task"].sudo(as_user.id).search([])

    def add_follower(self, entity, partner):
        as_user = entity.env.user
        return (
            self.env["mail.followers"]
            .sudo(as_user.id)
            .create(
                {
                    "partner_id": partner.id,
                    "res_id": entity.id,
                    "res_model": entity._name,
                }
            )
        )


class ProjectOwnUserPermissionTC(ProjectPermissionTC):
    "Test class for project creation permissions"

    def test_project_user_own_project(self):
        """Project users must be able to:
        - create their own project
        - configure it but not change its privacy_visibility field
        - add followers to it
        - add and remove columns to it
        - remove it
        """

        # Creation
        project = self.create_project(self.user1, name="myproject")
        self.assertEqual(project.user_id, self.user1)

        # Project managers can still see the project
        self.assertIn(project, self.seen_projects(self.project_manager))

        # Update config mostly OK
        project.name = "project new name"

        # can_write compute field is OK:
        self.assertTrue(project.can_write)

        # Add follower OK and gives read access
        self.add_follower(project, self.user2.partner_id)
        self.assertTrue(self.is_follower(self.user2, project))
        self.assertIn(project, self.seen_projects(self.user2))

        # Update privacy visibility not OK
        with self.assertRaises(AccessError) as err:
            project.privacy_visibility = "portal"
        self.assertEqual(
            err.exception.name,
            "Need to be a project manager to change a project's visibility.",
        )

        # Removal
        project.unlink()


class ProjectOtherUsersPermissions(ProjectPermissionTC):
    "Class for tests on other people's project access permissions"

    def setUp(self):
        super().setUp()

        self.project1 = self.create_project(self.user1, name="project1")
        self.project2 = self.create_project(self.user2, name="project2")

    def test_project_user_other_s_project_as_non_follower(self):
        """Project users must not be able to see a someone else's project if
        configured with the 'followers only' privacy_visibility
        """

        self.assertFalse(self.is_follower(self.user2, self.project1))
        self.assertNotIn(self.project1, self.seen_projects(self.user2))
        self.assertFalse(self.entity_as(self.project1, self.user2).can_write)

        self.project1.sudo().privacy_visibility = "portal"
        self.assertIn(self.project1, self.seen_projects(self.user2))

    def test_project_user_other_s_project_as_follower(self):
        """With another's user project, a follower user must not be able to:
        - change the project's configuration
        - add someone to the project's followers
        - add a task to the project
        - modify any task from the project (even tasks it did not create)
        - change task's stage
        - delete a task of the project
        - delete the project
        """

        p1_id = self.project1.id
        task1 = self.create_task(as_user=self.user1, name="Task1", project_id=p1_id)

        # Add user2 as project1 follower and check read perm
        self.add_follower(self.project1, self.user2.partner_id)
        self.assertIn(self.project1, self.seen_projects(self.user2))
        p1_as_user2 = self.entity_as(self.project1, self.user2)

        # Check can_write compute field is True:
        self.assertTrue(p1_as_user2.can_write)

        # Check user2 can modify project's name:
        p1_as_user2.name = "user2 given name"

        # Check user2 can add a follower:
        user3 = self.user2.copy({"login": "user3", "name": "user3"})
        self.add_follower(p1_as_user2, user3.partner_id)

        # Check user2 can see other's tasks, modify and remove them:
        self.assertIn(task1, self.seen_tasks(self.user2))
        t1_as_user2 = self.entity_as(task1, self.user2)
        t1_as_user2.description = "user2's description"
        t1_as_user2.unlink()

        # ... and create new ones:
        t2 = self.create_task(as_user=self.user2, name="Task2", project_id=p1_id)
        t2.unlink()

        # User2 cannot change project's user_id however:
        with self.assertRaises(AccessError) as err:
            p1_as_user2.user_id = self.user2.id
        self.assertIn("need to be a project manager", err.exception.name.lower())

        # .. and can remove the project:
        p1_as_user2.unlink()

    def test_privacy_employees_task_type_rule(self):
        "Any internal user in project user group can create, write and unlink task type"
        self.project1.sudo().privacy_visibility = "employees"

        self.assertTrue(1 in self.user1.groups_id.ids)
        task_type1 = self.create_task_type(
            as_user=self.user1,
            name="Task type 1",
            project_ids=[(6, 0, self.project1.ids)],
        )
        self.assertEquals(self.project1.ids, task_type1.project_ids.ids)

        tt1_as_user1 = self.entity_as(task_type1, self.user1)

        new_name = "New Name"
        tt1_as_user1.write({"name": new_name})
        self.assertEquals(task_type1.name, new_name)

        tt1_as_user1.unlink()

        # A user that is not in project user group can't create a task type
        self.user2.groups_id -= self.env.ref("project.group_project_user")
        with self.assertRaises(AccessError) as err:
            self.create_task_type(
                as_user=self.user2,
                name="Task type 2",
                project_ids=[(6, 0, self.project1.ids)],
            )
        self.assertIn(
            "Sorry, you are not allowed to create this kind of document.",
            err.exception.name,
        )
