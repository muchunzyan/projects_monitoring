{
    'name': 'Decidely',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Voting table',
    'author': 'Uchunzhyan Mikhail (CC BY-NC) 2025',
    'website': 'https://github.com/muchunzyan/projects_monitoring',
    'installable': True,
    'auto_install': True,
    'application': True,
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/export_template_poll.xml',
        'views/poll_poll_views.xml',
        'views/poll_menus.xml',
    ],
    'license': 'LGPL-3'
}
