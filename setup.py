import os
import sys
from setuptools import setup

version_py = os.path.join(os.path.dirname(__file__), 'trackhub', 'version.py')
version = open(version_py).read().strip().split('=')[-1].replace('"','')

long_description = """
Create and manage UCSC track hubs from Python
"""

if (sys.version_info[0] == 2) and (sys.version_info[1] < 7):
    install_requires.append('ordereddict')

setup(
    name="trackhub",
    version=version,
    install_requires=[i.strip() for i in open('requirements.txt')],
    packages=['trackhub',
              'trackhub.test',
              'trackhub.test.data',
              'trackhub.scripts'],
    author="Ryan Dale",
    description=long_description,
    long_description=long_description,
    url="http://github.com/daler/trackhub",
    package_data = {'trackhub':["test/data/*"]},
    package_dir = {"trackhub": "trackhub"},
    license = 'MIT',
    #scripts = ['trackhub/scripts/example_script.py'],
    author_email="dalerr@niddk.nih.gov",
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
