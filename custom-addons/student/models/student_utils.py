# This module defines shared utility classes and support models for the PaLMS system.
# Includes messaging helpers, degree naming logic, campus metadata, tagging, approval records, and faculty resolution.

from markupsafe import Markup
from odoo import api, fields, models, _  # _ is used for translations
from odoo.exceptions import UserError, ValidationError

# === UTILITY METHODS ===

class StudentUtils(models.AbstractModel):
    _name = 'student.utils'
    _description = 'PaLMS - Utility Methods'

    # Send a formatted message to a channel with optional creation
    @api.model
    def send_message(context, source, message_text, recipients, author, data_tuple=-1):
        tuple_id, tuple_name = data_tuple

        # Compose channel name based on source context
        if source == 'project':
            channel_name = "Project №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'application':
            channel_name = "Applicaton №" + tuple_id + " for " + tuple_name
        elif source == 'proposal':
            channel_name = "Project Proposal №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'task':
            channel_name = "Task №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'announcement':
            channel_name = "Announcement №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'milestone':
            channel_name = "Milestone №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'poll':
            channel_name = "Poll №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'review_table':
            channel_name = "Review Table №" + tuple_id + " (" + tuple_name + ")"
        elif source == 'review_line':
            channel_name = "Project Review: " + tuple_name
        elif source == 'calendar_event':
            channel_name = "Calendar Event №" + tuple_id + " (" + tuple_name + ")"
        else:
            raise ValueError(f"Unknown source type: {source}")

        # Reuse existing channel or create new one
        channel = context.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1)

        if not channel:
            channel = context.env['discuss.channel'].with_context(mail_create_nosubscribe=True).sudo().create({
                'channel_partner_ids': [(6, 0, author.partner_id.id)],
                'channel_type': 'channel',
                'name': channel_name,
                'display_name': channel_name
            })
            channel.write({
                'channel_partner_ids': [(4, recipient.partner_id.id) for recipient in recipients]
            })

        # Post message to the channel
        channel.sudo().message_post(
            body=Markup(message_text),
            author_id=author.partner_id.id,
            message_type="comment",
            subtype_xmlid='mail.mt_comment'
        )

    # Display client-side popup notification
    def message_display(self, title, message, sticky_bool):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(title),
                'message': message,
                'sticky': sticky_bool,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }

# === DEGREE DEFINITION ===

class StudentDegree(models.Model):
    _name = 'student.degree'
    _description = 'PaLMS - Degrees of Education'

    # Computed field for full degree description combining level and year
    name = fields.Char('Degree Description', readonly=True, compute="_form_name", store=True)
    level = fields.Selection([
        ('ba', "Bachelor's"),
        ('ms', "Master's"),
        ('phd', 'PhD')
    ], default="ba", string='Level of Education', required=True)
    year = fields.Selection([
        ('prep', 'Preparatory Year'),
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
        ('5', '5th Year'),
        ('6', '6th Year')
    ], default='1', string='Academic Year', required=True)

    # Associated projects for this degree
    project_ids = fields.Many2many('student.project', string='Projects for This Degree', readonly=True)

    @api.depends('level', 'year')
    def _form_name(self):
        # Format degree label from level and year
        text_dictionary = {
            "ba": "Bachelor's",
            "ms": "Master's",
            "phd": "PhD",
            "1": "1st Year",
            "2": "2nd Year",
            "3": "3rd Year",
            "4": "4th Year",
            "5": "5th Year",
            "6": "6th Year",
            "prep": "Preparatory Year"
        }
        for record in self:
            record.name = text_dictionary[record.level] + ' - ' + text_dictionary[record.year]

# === CAMPUS ENTITY ===

class StudentCampus(models.Model):
    _name = 'student.campus'
    _description = 'PaLMS - Campuses'

    # City where the campus is located
    name = fields.Char('City Name')
    # Name of the university at this campus
    university_name = fields.Char('University Name')
    # Legal address of the campus
    legal_address = fields.Text('Legal Address')
    # Faculties associated with this campus
    faculty_id = fields.One2many('student.faculty', 'campus', string='Faculties', readonly=True)
    # Projects associated with this campus
    project_ids = fields.Many2many('student.project', string='Projects', readonly=True)

# === TAGS FOR PROJECT FILTERING ===

class StudentTag(models.Model):
    _name = 'student.tag'
    _description = 'PaLMS - Tags'

    # Name of the tag
    name = fields.Char('Name', required=True)

# === SCIENTIFIC PROFILE REFERENCE ===

class StudentScientificProfile(models.Model):
    _name = 'student.scientific_profile'
    _description = 'PaLMS - Scientific Profiles'

    # Name of the scientific profile
    name = fields.Char('Name', required=True)

# === APPROVAL RECORD TRACKING ===

class StudentApproval(models.Model):
    _name = 'student.approval'
    _description = 'PaLMS - Approvals'

    # Computed name combining type, program, and degree
    name = fields.Char('Approval Record Name', compute="_compute_approval_name", store=True)
    type = fields.Selection([
        ('cw', 'Course Work (Курсовая работа)'),
        ('fqw', 'Final Qualifying Work (ВКР)'),
        ('both', 'Both (КР/ВКР)')
    ], string="Type", required=True)
    # Program associated with the approval
    program_id = fields.Many2one('student.program', string='Program', required=True)
    # Degree associated with the approval
    degree_id = fields.Many2one('student.degree', string='Degree', required=True)

    @api.depends('type', 'program_id', 'degree_id')
    def _compute_approval_name(self):
        # Format the approval name
        for record in self:
            type_label = {
                'cw': "КР",
                'fqw': "ВКР",
                'both': "КР/ВКР"
            }.get(record.type, "")
            record.name = f"{type_label} • {record.program_id.name} • {record.degree_id.name}"

# === EXTENSION OF MESSAGE SUBTYPES ===

class CustomMessageSubtype(models.Model):
    _name = 'student.message.subtype'
    _description = 'Student - Message Subtype'
    _inherit = 'mail.message.subtype'

# === FACULTY RESOLUTION FOR USER ACCOUNTS ===

class ResUsers(models.Model):
    _inherit = 'res.users'

    # Computed faculty field based on user groups
    faculty = fields.Many2one('student.faculty', string='Faculty', compute='_compute_faculty', store=True)

    @api.depends('groups_id')
    def _compute_faculty(self):
        for user in self:
            self.faculty = False
            # Determine faculty based on group membership
            if user.has_group('student.group_supervisor'):
                self.faculty = self.env['student.faculty'].sudo().search([('supervisor_ids', 'in', user.id)], limit=1)
            elif user.has_group('student.group_professor'):
                self.faculty = self.env['student.faculty'].sudo().search([('professor_ids', 'in', user.id)], limit=1)
            elif user.has_group('student.group_student'):
                self.faculty = self.env['student.faculty'].sudo().search([('student_ids', 'in', user.id)], limit=1)