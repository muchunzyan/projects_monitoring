from markupsafe import Markup
from odoo import models, fields, api

class Poll(models.Model):
    _name = 'poll.poll'
    _description = 'Decidely - Polls'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    option_ids = fields.One2many('poll.option', 'poll_id', string='Options', required=True)
    user_ids = fields.Many2many('res.users', string='Interviewed users', required=True)
    vote_ids = fields.One2many('poll.vote', 'poll_id', string='Votes')
    create_notification_sent = fields.Boolean(default=False, required=True)

    def _check_poll_votes_complete(self):
        for poll in self:
            if poll.vote_ids and all(v.vote for v in poll.vote_ids):
                message_text = Markup(f"All votes in poll <a href=\"/web#id={poll.id}&model=poll.poll&view_type=form\">{poll.name}</a> are completed.")
                poll.env['poll.utils'].send_message(
                    message_text,
                    poll.created_by,
                    poll.created_by,
                    (str(poll.id), str(poll.name))
                )

    def _send_poll_notification(self, update=False):
        if self.user_ids:
            if not update:
                message_text = Markup(f"A new poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been created for you. Please vote!")
            else:
                message_text = Markup(f"The poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been updated. Please vote!")

            self.env['poll.utils'].send_message(
                message_text,
                self.user_ids,
                self.created_by,
                (str(self.id), str(self.name))
            )

    def write(self, vals):
        if self.env.user != self.created_by:
            restricted_fields = set(vals.keys()) - {'vote_ids', 'visible_vote_ids'}
            if restricted_fields:
                raise models.ValidationError("Only the creator can modify these fields.")

        result = super().write(vals)

        if 'user_ids' in vals or 'option_ids' in vals:
            self.vote_ids.unlink()
            new_votes = []
            for user in self.user_ids:
                for option in self.option_ids:
                    new_votes.append((0, 0, {
                        'user_id': user.id,
                        'option_id': option.id,
                    }))
            self.vote_ids = new_votes

            if not self.create_notification_sent:
                self._send_poll_notification(update=False)
                self.create_notification_sent = True
            else:
                self._send_poll_notification(update=True)

        return result

    def unlink(self):
        for poll in self:
            if poll.created_by != self.env.user:
                raise models.ValidationError("Only the creator can delete the poll.")
        return super().unlink()

class PollOption(models.Model):
    _name = 'poll.option'
    _description = 'Decidely - Poll Options'

    name = fields.Char(required=True, translate=True)
    poll_id = fields.Many2one('poll.poll', required=True, ondelete='cascade')

class PollVote(models.Model):
    _name = 'poll.vote'
    _description = 'Decidely - Poll Votes'

    user_id = fields.Many2one('res.users', required=True)
    poll_id = fields.Many2one('poll.poll', required=True, ondelete='cascade')
    option_id = fields.Many2one('poll.option', required=True, ondelete='cascade')
    vote = fields.Selection([('yes', 'Yes'), ('maybe', 'Maybe'), ('no', 'No')])

    @api.model
    def create(self, vals):
        poll = self.env['poll.poll'].browse(vals.get('poll_id'))
        if self.env.user != poll.created_by:
            raise models.ValidationError("Only the poll creator can add new vote entries.")
        vote = super().create(vals)
        if vote.poll_id:
            vote.poll_id._check_poll_votes_complete()
        return vote

    def write(self, vals):
        for vote in self:
            if vote.user_id != self.env.user and vote.poll_id.created_by != self.env.user:
                raise models.ValidationError("You can only modify your own votes.")
        result = super().write(vals)
        for vote in self:
            if vote.poll_id:
                vote.poll_id._check_poll_votes_complete()
        return result

    def unlink(self):
        for vote in self:
            if vote.poll_id.created_by != self.env.user:
                raise models.ValidationError("Only the poll creator can delete vote entries.")
        return super().unlink()
