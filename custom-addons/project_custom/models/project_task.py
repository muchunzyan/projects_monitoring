from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    attachments = fields.Datetime(string='Attachments')