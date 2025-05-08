from odoo import models, fields, api
from odoo.exceptions import AccessError
from markupsafe import Markup

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
    student_milestone_id = fields.Many2one(
        'student.milestone',
        string='Milestone',
        ondelete='cascade',
        tracking=True,
        readonly=True
    )

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
            if not record.student_milestone_id:
                record.env['student.calendar.event'].sudo().create({
                    'name': f'Task: {record.name}',
                    'event_type': 'task',
                    'start_datetime': record.date_deadline,
                    'end_datetime': record.date_deadline,
                    'task_id': record.id,
                    'user_ids': [(6, 0, record.user_ids.ids)] if record.user_ids else []
                })
        return records

    def write(self, vals):
        if 'stage_id' in vals:
            stage_id = vals.get('stage_id')
            if stage_id:
                stage_name = self.env['project.task.type'].browse(stage_id).name
                if stage_name == 'Complete':
                    project = self.project_id
                    student_project = self.env['student.project'].search([('project_project_id', '=', project.id)], limit=1)
                    professor = student_project.professor_id if student_project else None
                    if professor and professor.professor_account:
                        # Send the email --------------------
                        subtype_id = self.env.ref('student.student_message_subtype_email')
                        template = self.env.ref('student.email_template_task_completed')
                        template.send_mail(self.id,
                                           email_values={'email_to': self.env['res.users'].search([('id', '=', professor.professor_account.id)]).email,
                                                         'subtype_id': subtype_id.id},
                                           force_send=True)
                        # -----------------------------------

                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        task_url = f'{base_url}/web#id={self.id}&model=project.task&view_type=form'

                        message_text = Markup(
                            f"The task has been marked as completed: <a href=\"{task_url}\">{self.name}</a>. Please review and approve it.")

                        self.env['mail.message'].create({
                            'model': 'project.task',
                            'res_id': self.id,
                            'message_type': 'notification',
                            'subtype_id': self.env.ref('mail.mt_note').id,
                            'body': message_text,
                            'author_id': self.env.user.partner_id.id,
                            'partner_ids': [(6, 0, [professor.professor_account.partner_id.id])],
                        })
                        self.env['student.utils'].send_message(
                            source='task',
                            message_text=message_text,
                            recipients=[professor.professor_account],
                            author=self.env.user,
                            data_tuple=(str(self.id), self.name)
                        )
                elif stage_name == 'Approved':
                    if not self.env.user.has_group('student.group_professor'):
                        raise AccessError("Only a professor can change the task status to Approved.")
        return super(ProjectTask, self).write(vals)