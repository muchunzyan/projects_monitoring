from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression

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
    channel_id = fields.Many2one('discuss.channel', string='Discuss Channel', readonly=True, copy=False)
    reply_ids = fields.One2many('student.announcement.reply', 'announcement_id', string='Replies')
    can_reply = fields.Boolean(string="Can Reply", compute='_compute_can_reply')

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

    @api.depends('target_group_ids', 'target_program_ids')
    def _compute_can_reply(self):
        current_user = self.env.user
        for rec in self:
            in_group = bool(set(current_user.groups_id.ids) & set(rec.target_group_ids.ids))
            student = self.env['student.student'].sudo().search([('student_account', '=', current_user.id)], limit=1)
            in_program = student and student.student_program.id in rec.target_program_ids.ids
            rec.can_reply = in_group and in_program

    @api.model
    def create(self, vals):
        self = self.with_context(skip_notification=True)
        record = super().create(vals)
        record._notify_target_users(is_update=False)
        return record

    def write(self, vals):
        res = super().write(vals)
        # Исключаем уведомление, если запись только что создана
        if self._origin.id and not self._context.get('skip_notification'):
            self._notify_target_users(is_update=True)
        return res

    def _notify_target_users(self, is_update=False):
        for announcement in self:
            # Находим студентов нужных программ
            students = self.env['student.student'].sudo().search([
                ('student_program', 'in', announcement.target_program_ids.ids)
            ])
            # Получаем аккаунты пользователей этих студентов
            program_user_ids = students.mapped('student_account.id')

            # Находим пользователей нужных групп
            group_user_ids = self.env['res.users'].sudo().search([
                ('groups_id', 'in', announcement.target_group_ids.ids)
            ]).ids

            # На пересечении программ и групп
            target_user_ids = list(set(program_user_ids) & set(group_user_ids))

            users = self.env['res.users'].browse(target_user_ids)
            if users:
                message_text = (
                    f'Объявление обновлено: {announcement.name}'
                    if is_update else
                    f'Новое объявление: {announcement.name}'
                )

                if is_update:
                    channel = announcement.channel_id
                else:
                    announcement.env['student.utils'].send_message(
                        'announcement',
                        message_text,
                        users,
                        announcement.author_id,
                        (str(announcement.id), str(announcement.name))
                    )
                    channel = announcement.env['discuss.channel'].sudo().search([
                        ('name', '=', f"Announcement №{announcement.id} ({announcement.name})")
                    ], limit=1)
                    announcement.channel_id = channel

                if is_update:
                    channel.sudo().message_post(
                        body=message_text,
                        author_id=announcement.author_id.partner_id.id,
                        message_type="comment",
                        subtype_xmlid='mail.mt_comment'
                    )

    def action_reply_to_announcement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reply to Announcement',
            'res_model': 'student.announcement.reply',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_announcement_id': self.id,
            }
        }

    def _search(self, domain, offset=0, limit=None, order=None):
        user = self.sudo().env.user
        if not (
                user.has_group('student.group_manager') or
                user.has_group('student.group_supervisor') or
                user.has_group('student.group_administrator') or
                user.has_group('base.group_system')
        ):
            student = self.env['student.student'].sudo().search([('student_account', '=', user.id)], limit=1)
            group_ids = user.groups_id.ids

            if student:
                domain = expression.AND([
                    domain,
                    [('target_program_ids', 'in', [student.student_program.id])],
                    [('target_group_ids', 'in', group_ids)],
                ])
            else:
                domain = expression.AND([
                    domain,
                    [('id', '=', -1)]
                ])
        return super()._search(domain, offset=offset, limit=limit, order=order)
