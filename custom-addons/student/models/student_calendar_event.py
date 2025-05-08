from email.policy import default

from markupsafe import Markup
from odoo import models, fields, api
from odoo.exceptions import AccessError

class StudentCalendarEvent(models.Model):
    _name = 'student.calendar.event'
    _description = 'PaLMS - Calendar Events'
    _order = 'start_datetime'

    name = fields.Char(string="Title", required=True)
    event_type = fields.Selection([
        ('task', 'Task'),
        ('commission', 'Commission'),
        ('announcement_deadline', 'Announcement Deadline'),
        ('milestone_deadline', 'Milestone Deadline'),
        ('custom', 'Other'),
    ], required=True, string="Event Type")
    description = fields.Text(string="Description")
    start_datetime = fields.Datetime(string="Start Time", required=True)
    end_datetime = fields.Datetime(string="End Time")

    announcement_id = fields.Many2one(
        'student.announcement',
        string='Related Announcement',
        ondelete='cascade'
    )
    task_id = fields.Many2one(
        'project.task',
        string='Related Task',
        ondelete='cascade'
    )
    milestone_id = fields.Many2one(
        'student.milestone',
        string='Related Milestone',
        ondelete='cascade'
    )
    commission_id = fields.Many2one(
        'student.commission',
        string='Related Commission',
        ondelete='cascade'
    )
    poll_id = fields.Many2one(
        'poll.poll',
        string='Related Poll',
        ondelete='cascade'
    )

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='student_calendar_event_user_rel',
        column1='event_id',
        column2='user_id',
        string='Participants'
    )

    color = fields.Integer(string="Color Index", default=4)

    creator_id = fields.Many2one('res.users', string='Creator', default=lambda self: self.env.user, readonly=True)
    can_edit = fields.Boolean(string="Can Edit", compute="_compute_can_edit", store=False, depends=['creator_id'])

    channel_id = fields.Many2one('discuss.channel', string='Discuss Channel', readonly=True, copy=False)
    creation_notification_sent = fields.Boolean(string='Creation Notification Sent', readonly=True, default=False)

    def _compute_can_edit(self):
        for record in self:
            record.can_edit = (
                record.creator_id == self.env.user or
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            )

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._notify_target_users(is_update=False)
        return record

    def write(self, vals):
        for rec in self:
            if rec.creator_id != self.env.user and not (
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            ):
                raise AccessError("You can only edit your own events or have manager rights.")

            if rec.creation_notification_sent:
                rec._notify_target_users(is_update=True)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.creator_id != self.env.user and not (
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            ):
                raise AccessError("You can only delete your own events or have manager rights.")
        return super().unlink()

    def _notify_target_users(self, is_update=False):
        for event in self:
            users = event.user_ids
            if users:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                event_url = f'{base_url}/web#id={event.id}&model=student.calendar.event&view_type=form'

                message_text = Markup(
                    f'Calendar event updated: <a href="{event_url}">{event.name}</a>'
                    if is_update else
                    f'New calendar event: <a href="{event_url}">{event.name}</a>'
                )

                if is_update:
                    channel = event.channel_id
                else:
                    # Send the email --------------------
                    subtype_id = self.env.ref('student.student_message_subtype_email')
                    template = self.env.ref('student.email_template_calendar_event_created')
                    template.send_mail(self.id,
                                       email_values={'email_to': ','.join(users.mapped('email')),
                                                     'subtype_id': subtype_id.id},
                                       force_send=True)
                    # -----------------------------------

                    event.env['student.utils'].send_message(
                        'calendar_event',
                        message_text,
                        users,
                        event.creator_id,
                        (str(event.id), str(event.name))
                    )
                    channel = event.env['discuss.channel'].sudo().search([
                        ('name', '=', f"Calendar Event №{event.id} ({event.name})")
                    ], limit=1)
                    event.channel_id = channel

                    event.creation_notification_sent = True

                if is_update:
                    channel.sudo().message_post(
                        body=message_text,
                        author_id=event.creator_id.partner_id.id,
                        message_type="comment",
                        subtype_xmlid='mail.mt_comment'
                    )
