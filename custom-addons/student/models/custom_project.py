from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    additional_files = fields.Many2many(
        comodel_name='ir.attachment',
        relation='custom_project_task_additional_files_rel',
        column1='task_id',
        column2='attachment_id',
        string='Attachments'
    )
    file_count = fields.Integer('Number of attached files', compute='_compute_file_count', readonly=True)

    date_deadline = fields.Datetime(string='Deadline', index=True, tracking=True, required=True)

    @api.depends('additional_files')
    def _compute_file_count(self):
        self.file_count = len(self.additional_files)