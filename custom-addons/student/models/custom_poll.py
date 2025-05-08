from odoo import api
from markupsafe import Markup
from odoo import models, fields, api


class Poll(models.Model):
    _inherit = 'poll.poll'

    faculty_ids = fields.Many2many('student.faculty', string='Faculties')

    @api.onchange('faculty_ids')
    def _onchange_faculty_ids(self):
        if self.faculty_ids:
            professors = self.env['student.professor'].search([('professor_faculty', 'in', self.faculty_ids.ids)])
            self.user_ids = [(6, 0, professors.mapped('professor_account.id'))]
        else:
            self.user_ids = [(5, 0, 0)]

    def _send_poll_notification(self, update=False):
        if self.user_ids:
            if not update:
                # Send the email --------------------
                subtype_id = self.env.ref('student.student_message_subtype_email')
                template = self.env.ref('student.email_template_poll_created')
                template.send_mail(self.id,
                                   email_values={'email_to': ','.join(self.user_ids.mapped('email')),
                                                 'subtype_id': subtype_id.id},
                                   force_send=True)
                # -----------------------------------

                message_text = Markup(
                    f"A new poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been created for you. Please vote!")
            else:
                message_text = Markup(
                    f"The poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been updated. Please vote!")

            self.env['student.utils'].send_message(
                'poll',
                message_text,
                self.user_ids,
                self.created_by,
                (str(self.id), str(self.name))
            )


class PollOption(models.Model):
    _inherit = 'poll.option'

    commission_id = fields.Many2one('student.commission', string='Commission', required=True, ondelete='cascade')

    @api.onchange('commission_id')
    def _onchange_commission_id(self):
        if self.commission_id:
            self.name = f'{self.commission_id.name} ({self.commission_id.meeting_date})'

class PollVote(models.Model):
    _inherit = 'poll.vote'

    calendar_event_id = fields.Many2one('student.calendar.event', string='Calendar Event', ondelete='set null')

    def write(self, vals):
        result = super().write(vals)
        for vote in self:
            if vote.poll_id:
                if vals.get('vote') in ['yes', 'maybe']:
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
                    if vote.calendar_event_id:
                        vote.calendar_event_id.unlink()
                        vote.calendar_event_id = False
        print(vals)
        return result