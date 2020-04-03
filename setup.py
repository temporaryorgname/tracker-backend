from setuptools import setup

setup(
    name='fitnessapp',
    version='1.0',
    description='Backend',
    packages=['fitnessapp'],
    install_requires=[
        'bcrypt',
        'boto3',
        'flasgger',
        'Flask',
        'Flask-Cors',
        'Flask-Login',
        'Flask-RESTful',
        'Flask-SQLAlchemy',
        'gunicorn',
        'numpy',
        'Pillow',
        'psycopg2-binary',
        'scikit-learn',
        'scipy',
        'SQLAlchemy',
        'tqdm',
        'Werkzeug==0.16',
        'tracker_data @ git+https://github.com/howardh/tracker-data.git@54dc006ace39e21e6e090875761c78e5e32a786d#egg=tracker_data',
        'tracker_database @ git+https://github.com/temporaryorgname/database.git@2ebe59342ae33c60611e147d5e833e2c58e0ea6d#egg=tracker_database'
    ]
)
