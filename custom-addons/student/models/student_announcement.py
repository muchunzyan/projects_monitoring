from odoo import fields, models, api

from odoo.exceptions import ValidationError

class Announcement(models.Model):
    _name = "student.announcement"
    _description = "PaLMS - Announcements"
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True, translate=True)
    content = fields.Html(string='Content', translate=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    publish_end_date = fields.Datetime(string='Publish Until', required=True)
    is_published = fields.Boolean(string='Published', default=True, required=True)
    author_id = fields.Many2one(
        comodel_name='res.users',
        string='Author',
        default=lambda self: self.env.user,
        readonly=True,
        required=True
    )
    target_group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Target Groups',
        required=True
    )
    target_program_ids = fields.Many2many(
        comodel_name='student.program',
        string='Target Programs',
        required=True
    )
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='announcement_attachment_rel',
        column1='announcement_id',
        column2='attachment_id',
        string='Attachments'
    )

    @api.constrains('publish_end_date')
    def _check_publish_end_date(self):
        for record in self:
            if record.publish_end_date and record.publish_end_date < fields.Datetime.now():
                raise ValidationError("Publish end date must be in the future.")

    @api.depends('publish_end_date')
    def _compute_is_published(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.publish_end_date and rec.publish_end_date < now:
                rec.is_published = False
