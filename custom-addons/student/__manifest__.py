# This manifest file defines the configuration for the PaLMS 2 Odoo module.
# It specifies metadata, dependencies, and the list of data and view files to be loaded.
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PaLMS 2',
    'version': '2.0.0',
    'category': 'Academic',
    'sequence': 15,
    'summary': 'A prototype ERP solution for handling Course works and Final qualification works submissions',
    'author': 'Uchunzhyan Mikhail (CC BY-NC) 2025',
    'website': 'https://github.com/muchunzyan/projects_monitoring',
    'installable': True,
    'auto_install': True,
    'application': True,
    'depends' : ['mail','project', 'poll'],
    'data': [
        'data/student_groups.xml',
        'data/student_email_templates.xml',
        'data/student_regulations.xml',
        'data/languages.xml',
        'data/company_details.xml',
        'security/ir.model.access.csv',
        'security/ir_group_inherit_export.xml',
        'views/student_application_views.xml',
        'views/student_availability_views.xml',
        'views/student_faculty_views.xml',
        'views/student_professor_views.xml',
        'views/student_program_views.xml',
        'views/student_project_views.xml',
        'views/student_proposal_views.xml',
        'views/student_student_views.xml',
        'views/student_supervisor_views.xml',
        'views/student_manager_views.xml',
        'views/student_util_views.xml',
        'views/student_commission_views.xml',
        'views/student_announcement_views.xml',
        'views/student_announcement_reply_views.xml',
        'views/student_calendar_event_views.xml',
        'views/student_milestone_views.xml',
        'views/student_milestone_result_views.xml',
        'views/student_projects_group_views.xml',
        'views/student_review_views.xml',
        'views/student_dashboard_views.xml',
        'views/student_menus.xml',
        'views/custom_project_views.xml',
        'views/custom_poll_views.xml',
        'data/import/student_degree.xml'
    ],
    'license': 'LGPL-3'
}
