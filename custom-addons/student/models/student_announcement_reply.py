from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression

# This model represents user replies to announcements in PaLMS.
class AnnouncementReply(models.Model):
    _name = 'student.announcement.reply'
    _description = 'PaLMS - Replies to Announcements'

    # Link to the related announcement
    announcement_id = fields.Many2one('student.announcement', string='Announcement', required=True, ondelete='cascade')

    # User who submitted the reply (auto-filled to current user)
    user_id = fields.Many2one('res.users', string='Submitted By', required=True, default=lambda self: self.env.user)

    # Attachments uploaded with the reply
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='announcement_reply_attachment_rel',
        column1='announcement_id',
        column2='attachment_id',
        string='Attachments'
    )

    # Optional comment field for the reply
    comment = fields.Text(string='Comment')

    # Timestamp when the reply was submitted
    submit_date = fields.Datetime(string='Submitted On', default=fields.Datetime.now, readonly=True, required=True)

    # Enforce one reply per user per announcement
    _sql_constraints = [
        ('unique_reply_per_user', 'unique(announcement_id, user_id)', 'You can only submit one reply per announcement.')
    ]

    # Override create to validate announcement_id and set attachments as public
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._make_attachments_public()

        # Retrieve announcement_id either from values or context
        announcement_id = vals.get('announcement_id') or self.env.context.get('default_announcement_id')
        if isinstance(announcement_id, (list, tuple)):
            announcement_id = announcement_id[0] if announcement_id else False
        if not announcement_id:
            raise ValidationError("Announcement ID is missing.")

        return record

    # Override write to ensure attachments are public after update
    def write(self, vals):
        res = super().write(vals)
        self._make_attachments_public()
        return res

    # Mark all attachments as public
    def _make_attachments_public(self):
        for reply in self:
            for attachment in reply.attachment_ids:
                attachment.sudo().write({'public': True})

    # Override search to restrict access to own replies unless privileged
    def _search(self, domain, offset=0, limit=None, order=None):
        user = self.sudo().env.user
        if not (
                user.has_group('student.group_manager') or
                user.has_group('student.group_supervisor') or
                user.has_group('student.group_administrator') or
                user.has_group('base.group_system')
        ):
            domain = expression.AND([domain, [('user_id', '=', user.id)]])
        return super()._search(domain, offset=offset, limit=limit, order=order)
