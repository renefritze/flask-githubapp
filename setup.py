"""
Flask-GitHubApp
-------------

Easy GitHub app integration for Sanic
"""
import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'sanic_githubapp/version.py'), 'r') as f:
    exec(f.read())


setup(
    name='Sanic-GitHubApp',
    version=__version__,
    url='https://github.com/bradshjg/flask-githubapp',
    license='MIT',
    author='Jimmy Bradshaw',
    author_email='james.g.bradshaw@gmail.com',
    description='Rapid GitHub app development in Python',
    long_description=__doc__,
    packages=['sanic_githubapp'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'sanic',
        'github3.py'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Framework :: Flask',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
