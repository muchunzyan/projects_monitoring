from odoo import models, fields, api
from odoo.exceptions import AccessError

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

    @api.onchange("additional_files")
    def _update_additional_ownership(self):
        # Makes the files public, may implement user-specific ownership in the future
        for attachment in self.additional_files:
            attachment.write({'public': True})

    @api.depends('additional_files')
    def _compute_file_count(self):
        self.file_count = len(self.additional_files)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.env['student.calendar.event'].sudo().create({
                'name': f'Задача: {record.name}',
                'event_type': 'task',
                'start_datetime': record.date_deadline,
                'end_datetime': record.date_deadline,
                'task_id': record.id,
                'user_ids': [(6, 0, record.user_ids.ids)] if record.user_ids else []
            })
        return records

    def write(self, vals):
        # Проверяем, меняется ли поле stage_id
        if 'stage_id' in vals:
            stage_id = vals.get('stage_id')
            if stage_id:
                stage_name = self.env['project.task.type'].browse(stage_id).name
                print("Stage name:", stage_name)
                if stage_name == 'Approved':
                    if not self.env.user.has_group('student.group_professor'):
                        raise AccessError("Only a professor can change the task status to Approved.")
        return super(ProjectTask, self).write(vals)