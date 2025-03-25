# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class TopicModel(models.Model):
#     _name = "topic_model"
#     _description = "Topic Model"
#     _rec_name = "title_en"
#
#     author_id = fields.Many2one("user_model", unique=True, string="Author")
#     initiative_topic = fields.Boolean(string="Initiative topic")
#     title_en = fields.Char(string="Title (en)")
#     title_ru = fields.Char(string="Title (ru)")
#     annotation = fields.Char(string="Annotation")
#     key_words = fields.Char(string="Key words")
#     work_purpose = fields.Char(string="Work purpose")
#     expected_results = fields.Char(string="Expected results")
#     work_type = fields.Selection([
#         ('project', 'Project'),
#         ('research', 'Research'),
#     ], default='project', string="Work type")
#     executor_type = fields.Selection([
#         ('individual', 'Individual'),
#         ('team', 'Team'),
#     ], default='individual', string="Executor type")
#     work_objectives = fields.Char(string="Work objectives")
#     applied_methods = fields.Char(string="Applied methods")
#     tools_used = fields.Char(string="Tools used")
#     additional_info = fields.Char(string="Additional info")
#     supervisor = fields.Many2one("user_model", unique=True, string="Supervisor")
#     approved = fields.Boolean(string="Approved")
#     academic_year_id = fields.Many2one("academic_year_model", unique=True, string="Academic year")
