from odoo import fields, models, api

class Dashboard(models.TransientModel):
    _name = 'student.dashboard'
    _description = 'PaLMS - Dashboards'

    model_name = fields.Selection([
        ('student.announcement', 'Announcements'),
        ('student.announcement.reply', 'Replies to Announcements'),
        ('student.application', 'Applications for Projects'),
        ('student.availability', 'Projects Availability'),
        ('student.calendar.event', 'Calendar Events'),
        ('student.commission', 'Commissions'),
        ('student.defense', 'Commission Defenses'),
        ('student.grade', 'Commission Grades'),
        ('student.faculty', 'Faculties'),
        ('student.manager', 'Managers'),
        ('student.milestone', 'Milestones'),
        ('student.milestone.result', 'Milestones Results'),
        ('student.professor', 'Professors'),
        ('student.program', 'Programs'),
        ('student.project', 'Projects'),
        ('student.projects.group', 'Projects Groups'),
        ('student.proposal', 'Project Proposals'),
        ('student.review.table', 'Review Tables'),
        ('student.review.line', 'Review Lines'),
        ('student.student', 'Students'),
        ('student.supervisor', 'Supervisors'),
        ('student.degree', 'Degrees of Education'),
        ('student.campus', 'Campuses'),
        ('student.tag', 'Tags'),
        ('student.scientific_profile', 'Scientific Profiles'),
        ('student.approval', 'Approvals'),

        ('project.project', 'Project'),
        ('project.task', 'Task'),

        ('poll.poll', 'Poll'),
        ('poll.option', 'Poll Options'),
        ('poll.vote', 'Poll Votes'),
    ], string='Model', required=True)

    group_by_field_id = fields.Many2one(
        'ir.model.fields',
        string='Group By',
        domain="[('model', '=', model_name), ('ttype', 'in', ('char', 'selection', 'many2one', 'boolean')), ('store', '=', True)]"
    )

    def action_open_graph(self):
        context = {}
        if self.group_by_field_id:
            context['graph_groupbys'] = [self.group_by_field_id.name]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': self.model_name,
            'view_mode': 'graph',
            'domain': [],
            'context': context,
        }

    @api.onchange('model_name')
    def _onchange_model_name(self):
        self.group_by_field_id = False
        return {
            'domain': {
                'metric_id': [
                    ('model', '=', self.model_name),
                    ('ttype', 'in', ('float', 'integer', 'monetary')),
                    ('store', '=', True),
                    ('name', '!=', 'id')
                ],
                'group_by_field_id': [('model', '=', self.model_name), ('ttype', 'in', ('char', 'selection', 'many2one', 'boolean')), ('store', '=', True)],
            }
        }