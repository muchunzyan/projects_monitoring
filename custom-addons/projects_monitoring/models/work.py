from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WorkModel(models.Model):
    _name = "work_model"
    _description = "Work Model"
    # _rec_name = "topic_id"

    topic_id = fields.Many2one("topic_model", unique=True, string="Topic")
    review = fields.Char(string="Review")
    admitted_to_protection = fields.Boolean(string="Admitted to protection")
    non_admission_reason = fields.Char(string="Non-admission reason")
    grade = fields.Integer(string="Grade")
