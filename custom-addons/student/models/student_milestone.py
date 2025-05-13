# This model defines project milestones in PaLMS.
# Milestones have a deadline, attachments, and are linked to academic programs.
# When created, tasks and calendar events are generated for all relevant student projects.
# Notifications are sent to professors, managers, supervisors, and students.

from odoo import models, fields, api
from markupsafe import Markup

class StudentMilestone(models.Model):
    _name = 'student.milestone'
    _description = 'PaLMS - Milestones'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Title of the milestone
    name = fields.Char(string="Name", required=True, translate=True, tracking=True)

    # Optional description of the milestone
    description = fields.Text(string="Description", translate=True)

    # Due date of the milestone
    deadline_date = fields.Datetime(string="Deadline", tracking=True, required=True)

    # Programs this milestone applies to
    program_ids = fields.Many2many('student.program', string="Target Programs", required=True)

    # User who created the milestone
    author_id = fields.Many2one(
        comodel_name='res.users',
        string='Author',
        default=lambda self: self.env.user,
        readonly=True,
        required=True
    )

    # Attached files
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='student_milestone_attachment_rel',
        column1='milestone_id',
        column2='attachment_id',
        string='Attachments'
    )

    # Linked discussion channel
    channel_id = fields.Many2one('discuss.channel', string='Discuss Channel', readonly=True, copy=False)

    # Flag to track if notification was sent at creation
    creation_notification_sent = fields.Boolean(string='Creation Notification Sent', readonly=True, default=False)

    @api.model
    def create(self, vals):
        # Override create to make attachments public, create related tasks/events, and send notifications
        record = super().create(vals)
        record._make_attachments_public()
        record.create_tasks_and_calendar_events_for_projects()
        record._send_milestone_notification(is_update=False)
        return record

    def _make_attachments_public(self):
        # Set all attachments linked to this milestone as public
        for announcement in self:
            for attachment in announcement.attachment_ids:
                attachment.write({'public': True})

    def create_tasks_and_calendar_events_for_projects(self):
        # For each milestone, create tasks for related student projects and a calendar event
        task = self.env['project.task']
        student_project = self.env['student.project']
        for milestone in self:
            # Find projects linked to the milestone's programs
            projects = student_project.search([('program_ids', 'in', milestone.program_ids.ids)])

            milestone_professors = []

            for project in projects:
                # Create a task in the related project for this milestone
                task.sudo().create({
                    'name': milestone.name,
                    'project_id': project.project_project_id.id,
                    'student_milestone_id': milestone.id,
                    'description': milestone.description,
                    'date_deadline': milestone.deadline_date,
                    'additional_files': [(6, 0, milestone.attachment_ids.ids)],
                    'partner_id': milestone.author_id.partner_id.id,
                    'user_ids': [(6, 0, list(filter(None, [
                        project.student_account.id,
                        project.professor_account.id
                    ])))]
                })
                milestone_professors.append(project.professor_account.id)

            # Find managers and supervisors linked to the milestone's programs
            milestone_managers = self.env['student.manager'].search([
                ('program_ids', 'in', milestone.program_ids.ids)
            ])
            milestone_supervisors = self.env['student.supervisor'].search([
                ('program_ids', 'in', milestone.program_ids.ids)
            ])
            administrative_stuff_ids = list(filter(
                None, milestone_managers.mapped('manager_account.id') +
                      milestone_supervisors.mapped('supervisor_account.id') +
                      milestone_professors
            ))

            # Create a calendar event for the milestone deadline
            self.env['student.calendar.event'].sudo().create({
                'name': f'Milestone deadline: {milestone.name}',
                'event_type': 'milestone_deadline',
                'start_datetime': milestone.deadline_date,
                'end_datetime': milestone.deadline_date,
                'milestone_id': milestone.id,
                'user_ids': [(6, 0, list(set(
                    projects.mapped('student_account.id')
                    + administrative_stuff_ids
                )))],
                'creator_id': self.env.user.id
            })

    def write(self, vals):
        # Override write to update related tasks, calendar events, and send notifications on milestone update
        res = super().write(vals)
        for milestone in self:
            if (milestone.creation_notification_sent and
                    any(field in vals for field in ['name', 'description', 'deadline_date', 'attachment_ids'])):
                # Update tasks linked to this milestone
                tasks = self.env['project.task'].search([('student_milestone_id', '=', milestone.id)])
                tasks.write({
                    'name': milestone.name,
                    'description': milestone.description,
                    'date_deadline': milestone.deadline_date,
                    'additional_files': [(6, 0, milestone.attachment_ids.ids)]
                })

                # Update calendar events linked to this milestone
                calendar_events = self.env['student.calendar.event'].search([('milestone_id', '=', milestone.id)])
                calendar_events.write({
                    'name': f'Milestone deadline: {milestone.name}',
                    'start_datetime': milestone.deadline_date,
                    'end_datetime': milestone.deadline_date,
                })

                # Send update notification
                self._send_milestone_notification(is_update=True)
        return res

    def _send_milestone_notification(self, is_update=False):
        # Send notification about milestone creation or update to relevant users
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for milestone in self:
            url = f'{base_url}/web#id={milestone.id}&model=student.milestone&view_type=form'

            message_text = Markup(f'Milestone {"updated" if is_update else "created"}: <a href="{url}">{milestone.name}</a>')

            # Find all users related to the milestone's programs (managers, supervisors, students, professors)
            projects = self.env['student.project'].search([
                ('program_ids', 'in', milestone.program_ids.ids)
            ])
            student_managers = self.env['student.manager'].search([
                ('program_ids', 'in', milestone.program_ids.ids)
            ])
            student_supervisors = self.env['student.supervisor'].search([
                ('program_ids', 'in', milestone.program_ids.ids)
            ])
            recipient_users = list(filter(
                None,
                student_managers.mapped('manager_account.id') +
                student_supervisors.mapped('supervisor_account.id') +
                projects.mapped('student_account.id') +
                projects.mapped('professor_account.id')
            ))

            users = self.env['res.users'].browse(recipient_users)

            if is_update:
                # For updates, post a message in the existing discussion channel
                channel = milestone.channel_id
            else:
                # For creation, send an email notification
                subtype_id = self.env.ref('student.student_message_subtype_email')
                template = self.env.ref('student.email_template_milestone_created')
                template.send_mail(self.id,
                                   email_values={'email_to': ','.join(users.mapped('email')),
                                                 'subtype_id': subtype_id.id},
                                   force_send=True)

                # Send an internal message to users
                milestone.env['student.utils'].send_message(
                    'milestone',
                    message_text,
                    users,
                    milestone.author_id,
                    (str(milestone.id), str(milestone.name))
                )
                # Find or create the discussion channel for this milestone
                channel = milestone.env['discuss.channel'].sudo().search([
                    ('name', '=', f"Milestone №{milestone.id} ({milestone.name})")
                ], limit=1)
                milestone.channel_id = channel

                # Mark notification as sent
                milestone.creation_notification_sent = True

            if is_update:
                # Post update message on the discussion channel
                channel.sudo().message_post(
                    body=message_text,
                    author_id=milestone.author_id.partner_id.id,
                    message_type="comment",
                    subtype_xmlid='mail.mt_comment'
                )

    def action_upload_result(self):
        # Open a form to upload milestone results by the current student user
        self.ensure_one()
        student_project = self.env['student.project'].search([
            ('student_account', '=', self.env.user.id),
            ('program_ids', 'in', self.program_ids.ids)
        ], limit=1)

        return {
            'name': 'Upload Milestone Result',
            'type': 'ir.actions.act_window',
            'res_model': 'student.milestone.result',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_milestone_id': self.id,
                'default_user_id': self.env.user.id,
                'default_student_project_id': student_project.id,
                'default_base_fields_readonly':
                    self.env.user.has_group('student.group_student') or
                    self.env.user.has_group('student.group_professor')
            }
        }

    def action_view_milestone_results(self):
        # Open a view to list all results submitted for this milestone
        self.ensure_one()
        return {
            'name': 'Milestone Results',
            'type': 'ir.actions.act_window',
            'res_model': 'student.milestone.result',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('milestone_id', '=', self.id)],
            'context': {'default_milestone_id': self.id}
        }
