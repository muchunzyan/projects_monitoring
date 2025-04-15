from odoo import models, fields
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
    commission_id = fields.Many2one(
        'student.commission',
        string='Related Commission',
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

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='student_calendar_event_user_rel',
        column1='event_id',
        column2='user_id',
        string='Participants'
    )

    creator_id = fields.Many2one('res.users', string='Creator', default=lambda self: self.env.user, readonly=True)
    can_edit = fields.Boolean(string="Can Edit", compute="_compute_can_edit")

    def _compute_can_edit(self):
        for record in self:
            record.can_edit = (
                record.creator_id == self.env.user or
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            )

    def write(self, vals):
        for rec in self:
            if rec.creator_id != self.env.user and not (
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            ):
                raise AccessError("You can only edit your own events or have manager rights.")
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.creator_id != self.env.user and not (
                self.env.user.has_group('student.group_manager') or
                self.env.user.has_group('student.group_administrator')
            ):
                raise AccessError("You can only delete your own events or have manager rights.")
        return super().unlink()
