from setuptools import setup, find_packages
import os


def read_requirements():
    req_file = os.path.join(os.path.dirname(__file__), "requirements_headless.txt")
    with open(req_file) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name='sharedir',
    version='2.0.0',
    description='A simple tool to share files and directories over LAN or internet.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Ujjawal Saini',
    author_email='spignelon@proton.me',
    url='https://github.com/spignelon/ShareDir',
    license='AGPL-3.0',
    packages=find_packages(),
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'sharedir = sharedir.sharedir:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',
        'Topic :: Communications :: File Sharing',
    ],
    python_requires='>=3.10',
    project_urls={
        'Homepage': 'https://github.com/spignelon/ShareDir',
        'Bug Tracker': 'https://github.com/spignelon/ShareDir/issues',
        'Source Code': 'https://github.com/spignelon/ShareDir/blob/main/sharedir/sharedir.py',
    },
)
