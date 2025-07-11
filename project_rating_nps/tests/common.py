class RatingTestMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        partner = cls.env.ref("base.partner_demo")

        project = cls.env["project.project"].create(
            {
                "name": "Test project",
                "rating_status": "stage",
            }
        )

        stage = cls.env["project.task.type"].create(
            {
                "name": "Test stage",
                "project_ids": [(6, 0, project.ids)],
            }
        )

        cls.task = cls.env["project.task"].create(
            {
                "name": "test task",
                "project_id": project.id,
                "stage_id": stage.id,
                "partner_id": partner.id,
            }
        )

        cls.rating = cls.env["rating.rating"].create(
            {
                "res_model_id": cls.env["ir.model"]._get("project.task").id,
                "res_model": "project.task",
                "res_id": cls.task.id,
                "parent_res_model_id": cls.env["ir.model"]._get("project.project").id,
                "parent_res_id": project.id,
                "rated_partner_id": partner.id,
                "partner_id": partner.id,
                "rating": 8,
                "consumed": False,
            }
        )
