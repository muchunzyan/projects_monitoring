from odoo import api
from markupsafe import Markup
from odoo import models, fields, api


# Extend the base Poll model to include faculty selection and enhanced notification logic
class Poll(models.Model):
    _inherit = 'poll.poll'

    # Faculties associated with this poll (used to filter target professors)
    faculty_ids = fields.Many2many('student.faculty', string='Faculties')

    # When faculty_ids change, automatically assign professors to the poll
    @api.onchange('faculty_ids')
    def _onchange_faculty_ids(self):
        if self.faculty_ids:
            # Find professors linked to selected faculties
            professors = self.env['student.professor'].search([('professor_faculty', 'in', self.faculty_ids.ids)])
            # Assign their user accounts to the poll
            self.user_ids = [(6, 0, professors.mapped('professor_account.id'))]
        else:
            # Clear the user list if no faculties selected
            self.user_ids = [(5, 0, 0)]

    # Send email and Discuss messages when the poll is created or updated
    def _send_poll_notification(self, update=False):
        if self.user_ids:
            if not update:
                # Email notification via predefined template and subtype
                subtype_id = self.env.ref('student.student_message_subtype_email')
                template = self.env.ref('student.email_template_poll_created')
                template.send_mail(self.id,
                                   email_values={'email_to': ','.join(self.user_ids.mapped('email')),
                                                 'subtype_id': subtype_id.id},
                                   force_send=True)
                message_text = Markup(
                    f"A new poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been created for you. Please vote!")
            else:
                message_text = Markup(
                    f"The poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been updated. Please vote!")

            # Send notification to users via Discuss
            self.env['student.utils'].send_message(
                'poll',
                message_text,
                self.user_ids,
                self.created_by,
                (str(self.id), str(self.name))
            )


# Extend PollOption to associate it with a student commission
class PollOption(models.Model):
    _inherit = 'poll.option'

    # The commission linked to this poll option
    commission_id = fields.Many2one('student.commission', string='Commission', required=True, ondelete='cascade')

    # Automatically set the option name when a commission is selected
    @api.onchange('commission_id')
    def _onchange_commission_id(self):
        if self.commission_id:
            self.name = f'{self.commission_id.name} ({self.commission_id.meeting_date})'


# Extend PollVote to link it with a calendar event
class PollVote(models.Model):
    _inherit = 'poll.vote'

    # Calendar event created based on the vote
    calendar_event_id = fields.Many2one('student.calendar.event', string='Calendar Event', ondelete='set null')

    # Override write method to create or remove calendar events based on vote
    def write(self, vals):
        result = super().write(vals)
        for vote in self:
            if vote.poll_id:
                if vals.get('vote') in ['yes', 'maybe']:
                    # Create a calendar event for positive votes
                    event = self.env['student.calendar.event'].sudo().create({
                        'name': f'Possible Commission: {vote.option_id.commission_id.name}',
                        'event_type': 'commission',
                        'poll_id': self.poll_id.id,
                        'start_datetime': vote.option_id.commission_id.meeting_date,
                        'end_datetime': vote.option_id.commission_id.meeting_date,
                        'commission_id': vote.option_id.commission_id.id,
                        'user_ids': [(6, 0, [vote.user_id.id])],
                        'creator_id': self.env.user.id,
                        'color': 0
                    })
                    vote.calendar_event_id = event.id
                elif vals.get('vote') in ['no', False]:
                    # Delete the event if the vote was changed to 'no' or cleared
                    if vote.calendar_event_id:
                        vote.calendar_event_id.unlink()
                        vote.calendar_event_id = False
        return result