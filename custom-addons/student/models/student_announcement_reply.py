from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression

class AnnouncementReply(models.Model):
    _name = 'student.announcement.reply'
    _description = 'PaLMS - Replies to Announcements'

    announcement_id = fields.Many2one('student.announcement', string='Announcement', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Submitted By', required=True, default=lambda self: self.env.user)
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='announcement_reply_attachment_rel',
        column1='announcement_id',
        column2='attachment_id',
        string='Attachments'
    )
    comment = fields.Text(string='Comment')
    submit_date = fields.Datetime(string='Submitted On', default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        ('unique_reply_per_user', 'unique(announcement_id, user_id)', 'You can only submit one reply per announcement.')
    ]

    @api.model
    def create(self, vals):
        self._make_attachments_public()

        announcement_id = vals.get('announcement_id') or self.env.context.get('default_announcement_id')
        if isinstance(announcement_id, (list, tuple)):
            announcement_id = announcement_id[0] if announcement_id else False
        if not announcement_id:
            raise ValidationError("Announcement ID is missing.")

        return super().create(vals)

    def write(self, vals):
        self._make_attachments_public()
        return super().write(vals)

    def _make_attachments_public(self):
        for announcement in self:
            for attachment in announcement.attachment_ids:
                attachment.write({'public': True})

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
