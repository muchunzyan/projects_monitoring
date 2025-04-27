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
