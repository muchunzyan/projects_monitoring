from odoo import models, fields, api
from markupsafe import Markup


class ReviewTable(models.Model):
    _name = 'student.review.table'
    _description = 'PaLMS - Review Tables'
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, default=lambda self: 'New Review Table')
    program_ids = fields.Many2many('student.program', string='Programs', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='State', default='draft', tracking=True, compute='_compute_state', store=True, readonly=True, required=True)
    creator_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True, required=True)
    line_ids = fields.One2many('student.review.line', 'table_id', string='Review Lines')
    professor_ids = fields.Many2many('res.users', string='Professors', readonly=True)

    @api.depends('line_ids.reviewer_id', 'line_ids')
    def _compute_state(self):
        for record in self:
            if not record.line_ids:
                record.state = 'draft'
            elif all(line.reviewer_id for line in record.line_ids):
                record.state = 'completed'
            else:
                record.state = 'in_progress'

    @api.onchange('program_ids')
    def _onchange_program_ids(self):
        self.line_ids = [(5, 0, 0)]

    def action_generate_review_lines(self):
        for table in self:
            table.line_ids.unlink()

            projects = self.env['student.project'].search([
                ('project_report_file', '!=', False),
                ('plagiarism_check_file', '!=', False),
                ('student_feedback', '!=', False),
                ('program_ids', 'in', table.program_ids.ids),
            ])

            lines = []
            for project in projects:
                lines.append((0, 0, {
                    'project_id': project.id,
                }))

            table.write({'line_ids': lines})

            if lines:
                message_text = Markup(
                    f"A new review table <a href=\"/web#id={table.id}&model=student.review.table&view_type=form\">{table.name}</a> has been created. Please select projects for review!")
                professors = self.env['student.professor'].search([
                    ('professor_faculty.program_ids', 'in', table.program_ids.ids)
                ]).mapped('professor_account')
                table.env['student.utils'].send_message(
                    'review_table',
                    message_text,
                    professors,
                    table.creator_id,
                    (str(table.id), str(table.name))
                )

                table.professor_ids = [(6, 0, professors.ids)]

    def check_review_completion(self):
        for table in self:
            if table.state == 'completed':
                message_text = Markup(
                    f"All reviews have been selected for the table <a href=\"/web#id={table.id}&model=student.review.table&view_type=form\">{table.name}</a>.")
                table.env['student.utils'].send_message(
                    'review_table',
                    message_text,
                    [table.creator_id],
                    table.creator_id,
                    (str(table.id), str(table.name))
                )

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            record.check_review_completion()
        return result


class ReviewLine(models.Model):
    _name = 'student.review.line'
    _description = 'PaLMS - Student Review Lines'

    table_id = fields.Many2one('student.review.table', string='Review Table', required=True, ondelete='cascade')
    project_id = fields.Many2one('student.project', string='Project', required=True)
    reviewer_id = fields.Many2one('student.professor', string='Reviewer')

    _sql_constraints = [
        ('unique_project_in_table', 'unique(project_id, table_id)', 'Each project can appear only once in the same review table.')
    ]
