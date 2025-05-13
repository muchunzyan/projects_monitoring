# This model defines a logical grouping of student projects in PaLMS.
# It allows related projects to be managed together under a single group name.

from odoo import models, fields

class StudentProjectsGroup(models.Model):
    _name = 'student.projects.group'
    _description = 'PaLMS - Projects Groups'

    # Name of the project group
    name = fields.Char(string="Group Name", required=True)

    # List of projects that belong to this group
    project_ids = fields.One2many('student.project', 'projects_group_id', string="Projects", required=True)
