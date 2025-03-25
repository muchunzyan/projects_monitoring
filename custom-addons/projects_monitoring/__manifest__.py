{
    'name': 'Projects monitoring',
    'version': '1.0',
    'category': 'Human Resources/Student',
    'description': "Description",
    'author': "Uchunzhyan Mikhail",
    'depends': ['base', 'mail', 'student'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv'
        # 'views/projects_monitoring.xml',
        # 'views/work.xml',
        # 'views/topic.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}