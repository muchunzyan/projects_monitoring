from markupsafe import Markup
from odoo import models, fields, api

# Main model representing a poll
class Poll(models.Model):
    _name = 'poll.poll'
    _description = 'Decidely - Polls'

    # Poll title (translatable)
    name = fields.Char(required=True, translate=True)
    # Optional description of the poll (translatable)
    description = fields.Text(translate=True)
    # User who created the poll (automatically set to current user)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    # List of options available in this poll
    option_ids = fields.One2many('poll.option', 'poll_id', string='Options', required=True)
    # Users invited to vote
    user_ids = fields.Many2many('res.users', string='Interviewed users', required=True)
    # List of submitted votes
    vote_ids = fields.One2many('poll.vote', 'poll_id', string='Votes')
    # Flag to prevent duplicate notification after poll creation
    create_notification_sent = fields.Boolean(default=False, required=True)

    # Check if all votes are submitted and notify the poll creator
    def _check_poll_votes_complete(self):
        for poll in self:
            if poll.vote_ids and all(v.vote for v in poll.vote_ids):
                message_text = Markup(f"All votes in poll <a href=\"/web#id={poll.id}&model=poll.poll&view_type=form\">{poll.name}</a> are completed.")
                poll.env['poll.utils'].send_message(
                    'poll',
                    message_text,
                    poll.user_ids,
                    poll.created_by,
                    (str(poll.id), str(poll.name))
                )

    # Send notification to users about poll creation or update
    def _send_poll_notification(self, update=False):
        if self.user_ids:
            if not update:
                message_text = Markup(f"A new poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been created for you. Please vote!")
            else:
                message_text = Markup(f"The poll <a href=\"/web#id={self.id}&model=poll.poll&view_type=form\">{self.name}</a> has been updated. Please vote!")

            self.env['poll.utils'].send_message(
                'poll',
                message_text,
                self.user_ids,
                self.created_by,
                (str(self.id), str(self.name))
            )

    # Override write method to control permissions and regenerate votes
    def write(self, vals):
        # Restrict updates to poll creator
        if self.env.user != self.created_by:
            restricted_fields = set(vals.keys()) - {'vote_ids', 'visible_vote_ids'}
            if restricted_fields:
                raise models.ValidationError("Only the creator can modify these fields.")

        result = super().write(vals)

        # If users or options changed, regenerate vote entries
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

            # Send appropriate notification
            if not self.create_notification_sent:
                self._send_poll_notification(update=False)
                self.create_notification_sent = True
            else:
                self._send_poll_notification(update=True)

        return result

    # Restrict deletion to poll creator
    def unlink(self):
        for poll in self:
            if poll.created_by != self.env.user:
                raise models.ValidationError("Only the creator can delete the poll.")
        return super().unlink()

# Model representing an option in a poll
class PollOption(models.Model):
    _name = 'poll.option'
    _description = 'Decidely - Poll Options'

    # Option label (translatable)
    name = fields.Char(required=True, translate=True)
    # Related poll
    poll_id = fields.Many2one('poll.poll', required=True, ondelete='cascade')

# Model representing an individual vote
class PollVote(models.Model):
    _name = 'poll.vote'
    _description = 'Decidely - Poll Votes'

    # User who cast the vote
    user_id = fields.Many2one('res.users', required=True)
    # Related poll
    poll_id = fields.Many2one('poll.poll', required=True, ondelete='cascade')
    # Selected option
    option_id = fields.Many2one('poll.option', required=True, ondelete='cascade')
    # Vote value
    vote = fields.Selection([('yes', 'Yes'), ('maybe', 'Maybe'), ('no', 'No')])

    # Restrict vote creation to poll creator
    @api.model
    def create(self, vals):
        poll = self.env['poll.poll'].browse(vals.get('poll_id'))
        if self.env.user != poll.created_by:
            raise models.ValidationError("Only the poll creator can add new vote entries.")
        vote = super().create(vals)
        if vote.poll_id:
            vote.poll_id._check_poll_votes_complete()
        return vote

    # Restrict editing votes to vote owner or poll creator
    def write(self, vals):
        for vote in self:
            if vote.user_id != self.env.user and vote.poll_id.created_by != self.env.user:
                raise models.ValidationError("You can only modify your own votes.")
        result = super().write(vals)
        for vote in self:
            if vote.poll_id:
                vote.poll_id._check_poll_votes_complete()
        return result

    # Restrict deletion to poll creator
    def unlink(self):
        for vote in self:
            if vote.poll_id.created_by != self.env.user:
                raise models.ValidationError("Only the poll creator can delete vote entries.")
        return super().unlink()
