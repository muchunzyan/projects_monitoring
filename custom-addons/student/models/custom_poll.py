from markupsafe import Markup
from odoo import models, fields, api

class PollOption(models.Model):
    _inherit = 'poll.option'

    name = fields.Char(required=True, translate=True)
    commission_id = fields.Many2one('student.commission', string='Commission', required=True, ondelete='cascade')

    @api.onchange('commission_id')
    def _onchange_commission_id(self):
        if self.commission_id:
            self.name = f'{self.commission_id.name} ({self.commission_id.meeting_date})'


class Poll(models.Model):
    _inherit = 'poll.poll'

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
