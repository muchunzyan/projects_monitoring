from odoo import models, fields

class StudentProjectsGroup(models.Model):
    _name = 'student.projects.group'
    _description = 'PaLMS - Projects Groups'

    name = fields.Char(string="Group Name", required=True)
    project_ids = fields.One2many('student.project', 'projects_group_id', string="Projects", required=True)
