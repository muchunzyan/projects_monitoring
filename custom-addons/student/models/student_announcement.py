from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression
from markupsafe import Markup

class Announcement(models.Model):
    _name = "student.announcement"
    _description = "PaLMS - Announcements"
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True, translate=True)
    content = fields.Html(string='Content', translate=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    deadline_date = fields.Datetime(string='Deadline', required=True,
                                    help='At this time, the announcement will be taken off the publication')
    is_published = fields.Boolean(string='Published', default=True, reqired=True, store=True, readonly=True)
    author_id = fields.Many2one(
        comodel_name='res.users',
        string='Author',
        default=lambda self: self.env.user,
        readonly=True,
        required=True
    )
    target_group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Target Groups',
        required=True
    )
    target_program_ids = fields.Many2many(
        comodel_name='student.program',
        string='Target Programs',
        required=True
    )
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='student_announcement_attachment_rel',
        column1='announcement_id',
        column2='attachment_id',
        string='Attachments'
    )
    channel_id = fields.Many2one('discuss.channel', string='Discuss Channel', readonly=True, copy=False)
    reply_ids = fields.One2many('student.announcement.reply', 'announcement_id', string='Replies')

    creation_notification_sent = fields.Boolean(string='Creation Notification Sent', readonly=True, default=False)

    @api.constrains('deadline_date')
    def _check_deadline_date(self):
        for record in self:
            if record.deadline_date and record.deadline_date < fields.Datetime.now():
                raise ValidationError("Deadline date must be in the future.")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._make_attachments_public()
        record._notify_target_users(is_update=False)
        return record

    def write(self, vals):
        res = super().write(vals)
        self._make_attachments_public()

        for rec in self:
            if rec.creation_notification_sent:
                self._notify_target_users(is_update=True)

        return res

    def _make_attachments_public(self):
        for announcement in self:
            for attachment in announcement.attachment_ids:
                attachment.write({'public': True})

    def _notify_target_users(self, is_update=False):
        for announcement in self:
            if announcement.is_published:
                students = self.env['student.student'].sudo().search(
                    [('student_program', 'in', announcement.target_program_ids.ids)])
                program_students_user_ids = students.mapped('student_account.id')

                managers = self.env['student.manager'].sudo().search(
                    [('program_ids', 'in', announcement.target_program_ids.ids)])
                program_managers_user_ids = managers.mapped('manager_account.id')

                supervisors = self.env['student.supervisor'].sudo().search(
                    [('program_ids', 'in', announcement.target_program_ids.ids)])
                program_supervisors_user_ids = supervisors.mapped('supervisor_account.id')

                faculties = self.env['student.faculty'].sudo().search(
                        [('program_ids', 'in', announcement.target_program_ids.ids)])
                professors = self.env['student.professor'].sudo().search(
                    [('professor_faculty', 'in', faculties.ids)])
                faculty_professors_user_ids = professors.mapped('professor_account.id')

                group_user_ids = self.env['res.users'].sudo().search([
                    ('groups_id', 'in', announcement.target_group_ids.ids)
                ]).ids

                program_and_faculty_users = (
                        set(program_students_user_ids) |
                        set(program_managers_user_ids) |
                        set(program_supervisors_user_ids) |
                        set(faculty_professors_user_ids))
                target_user_ids = list(program_and_faculty_users & set(group_user_ids))

                users = self.env['res.users'].browse(target_user_ids)
                if users:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    announcement_url = f'{base_url}/web#id={announcement.id}&model=student.announcement&view_type=form'

                    message_text = Markup(
                        f'Announcement updated: <a href="{announcement_url}">{announcement.name}</a>'
                        if is_update else
                        f'New announcement: <a href="{announcement_url}">{announcement.name}</a>'
                    )

                    if is_update:
                        channel = announcement.channel_id
                    else:
                        # Send the email --------------------
                        subtype_id = self.env.ref('student.student_message_subtype_email')
                        template = self.env.ref('student.email_template_announcement_created')
                        template.send_mail(self.id,
                                           email_values={'email_to': ','.join(users.mapped('email')),
                                                         'subtype_id': subtype_id.id},
                                           force_send=True)
                        # -----------------------------------

                        announcement.env['student.utils'].send_message(
                            'announcement',
                            message_text,
                            users,
                            announcement.author_id,
                            (str(announcement.id), str(announcement.name))
                        )
                        channel = announcement.env['discuss.channel'].sudo().search([
                            ('name', '=', f"Announcement №{announcement.id} ({announcement.name})")
                        ], limit=1)
                        announcement.channel_id = channel

                        announcement.creation_notification_sent = True

                    if is_update:
                        channel.sudo().message_post(
                            body=message_text,
                            author_id=announcement.author_id.partner_id.id,
                            message_type="comment",
                            subtype_xmlid='mail.mt_comment'
                        )
                    else:
                        # Create calendar event
                        self.env['student.calendar.event'].sudo().create({
                            'name': f'Announcement deadline: {announcement.name}',
                            'event_type': 'announcement_deadline',
                            'start_datetime': announcement.deadline_date,
                            'end_datetime': announcement.deadline_date,
                            'announcement_id': announcement.id,
                            'user_ids': [(6, 0, users.ids)],
                            'creator_id': self.env.user.id
                        })

    def action_reply_to_announcement(self):
        self.ensure_one()
        if not self.is_published:
            raise ValidationError("You can't send a reply to an irrelevant announcement.")

        user = self.env.user
        existing_reply = self.env['student.announcement.reply'].search([
            ('announcement_id', '=', self.id),
            ('user_id', '=', user.id)
        ], limit=1)

        if existing_reply:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Your Reply',
                'res_model': 'student.announcement.reply',
                'res_id': existing_reply.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reply to Announcement',
                'res_model': 'student.announcement.reply',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_announcement_id': self.id,
                }
            }

    def action_view_announcement_replies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Replies',
            'res_model': 'student.announcement.reply',
            'view_mode': 'list,form',
            'domain': [('announcement_id', '=', self.id)],
            'context': {
                'default_announcement_id': self.id,
            },
            'target': 'current',
        }

    def _search(self, domain, offset=0, limit=None, order=None):
        user = self.sudo().env.user
        if not (
                user.has_group('student.group_manager') or
                user.has_group('student.group_supervisor') or
                user.has_group('student.group_administrator') or
                user.has_group('base.group_system')
        ):
            group_ids = user.groups_id.ids
            domain = expression.AND([
                domain,
                [('target_group_ids', 'in', group_ids)],
                [('is_published', '=', True)]
            ])

            if user.has_group('student.group_student'):
                student = self.env['student.student'].sudo().search([('student_account', '=', user.id)], limit=1)
                if student:
                    domain = expression.AND([
                        domain,
                        [('target_program_ids', 'in', [student.student_program.id])]
                    ])
                else:
                    domain = expression.AND([
                        domain,
                        [('id', '=', -1)]
                    ])
            elif user.has_group('student.group_professor'):
                professor = self.env['student.professor'].sudo().search([('professor_account', '=', user.id)], limit=1)
                faculty_programs = self.env['student.program'].sudo().search([('program_faculty_id', '=', professor.professor_faculty.id)])

                if professor and faculty_programs:
                    domain = expression.AND([
                        domain,
                        [('target_program_ids', 'in', faculty_programs.ids)]
                    ])
                else:
                    domain = expression.AND([
                        domain,
                        [('id', '=', -1)]
                    ])
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def _cron_unpublish_expired_announcements(self):
        now = fields.Datetime.now()
        expired_announcements = self.search([
            ('is_published', '=', True),
            ('deadline_date', '<=', now)
        ])
        expired_announcements.write({'is_published': False})
