# This model defines calendar events in PaLMS for scheduling and notifying users about project-related activities.
# Events may relate to tasks, commissions, announcements, polls, or milestones and support access control and notifications.

from email.policy import default

from markupsafe import Markup
from odoo import models, fields, api
from odoo.exceptions import AccessError


class StudentCalendarEvent(models.Model):
    _name = 'student.calendar.event'
    _description = 'PaLMS - Calendar Events'
    _order = 'start_datetime'

    # Event title
    name = fields.Char(string="Title", required=True)

    # Categorize the type of event
    event_type = fields.Selection([
        ('task', 'Task'),
        ('commission', 'Commission'),
        ('announcement_deadline', 'Announcement Deadline'),
        ('milestone_deadline', 'Milestone Deadline'),
        ('custom', 'Other'),
    ], required=True, string="Event Type")

    # Optional description field
    description = fields.Text(string="Description")

    # Start and end datetime for the event
    start_datetime = fields.Datetime(string="Start Time", required=True)
    end_datetime = fields.Datetime(string="End Time")

    # Optional references to related objects
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

    # Users participating in this event
    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='student_calendar_event_user_rel',
        column1='event_id',
        column2='user_id',
        string='Participants'
    )

    # Visual color index for calendar display
    color = fields.Integer(string="Color Index", default=4)

    # Creator of the event (readonly)
    creator_id = fields.Many2one('res.users', string='Creator', default=lambda self: self.env.user, readonly=True)

    # Flag indicating whether the current user can edit the event
    can_edit = fields.Boolean(string="Can Edit", compute="_compute_can_edit", store=False, depends=['creator_id'])

    # Optional discussion channel attached to the event
    channel_id = fields.Many2one('discuss.channel', string='Discuss Channel', readonly=True, copy=False)

    # Prevent duplicate notifications
    creation_notification_sent = fields.Boolean(string='Creation Notification Sent', readonly=True, default=False)

    # Determine edit rights for the current user
    def _compute_can_edit(self):
        for record in self:
            record.can_edit = (
                record.creator_id == self.env.user or
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            )

    # Override create to notify users when the event is created
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._notify_target_users(is_update=False)
        return record

    # Override write to restrict editing to creator/admins and send update notifications
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

    # Override unlink to enforce deletion rights
    def unlink(self):
        for rec in self:
            if rec.creator_id != self.env.user and not (
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            ):
                raise AccessError("You can only delete your own events or have manager rights.")
        return super().unlink()

    # Notify users via email and discuss messages
    def _notify_target_users(self, is_update=False):
        for event in self:
            users = event.user_ids
            if users:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                event_url = f'{base_url}/web#id={event.id}&model=student.calendar.event&view_type=form'

                # Create the message content
                message_text = Markup(
                    f'Calendar event updated: <a href="{event_url}">{event.name}</a>'
                    if is_update else
                    f'New calendar event: <a href="{event_url}">{event.name}</a>'
                )

                if is_update:
                    # Post update message to existing channel
                    channel = event.channel_id
                else:
                    # Send email to users using email template
                    subtype_id = self.env.ref('student.student_message_subtype_email')
                    template = self.env.ref('student.email_template_calendar_event_created')
                    template.send_mail(self.id,
                                       email_values={'email_to': ','.join(users.mapped('email')),
                                                     'subtype_id': subtype_id.id},
                                       force_send=True)

                    # Send internal discuss message
                    event.env['student.utils'].send_message(
                        'calendar_event',
                        message_text,
                        users,
                        event.creator_id,
                        (str(event.id), str(event.name))
                    )

                    # Link or create discuss channel
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
