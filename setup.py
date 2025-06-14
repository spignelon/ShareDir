from setuptools import setup, find_packages

setup(
    name='sharedir',
    version='1.0.2',
    description='A simple tool to share files and directories over LAN or internet.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Ujjawal Saini',
    author_email='spignelon@proton.me',
    url='https://github.com/spignelon/ShareDir',
    license='AGPL-3.0',
    packages=find_packages(),
    install_requires=[
        'blinker==1.8.2',
        'click==8.1.7',
        'diceware==0.10',
        'Flask==3.0.3',
        'itsdangerous==2.2.0',
        'Jinja2==3.1.6',
        'MarkupSafe==2.1.5',
        'pypng==0.20220715.0',
        'qrcode==7.4.2',
        'setuptools==78.1.1',
        'typing_extensions==4.12.2',
        'Werkzeug==3.0.6'
    ],
    entry_points={
        'console_scripts': [
            'sharedir = sharedir.sharedir:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',
        'Topic :: Communications :: File Sharing',
    ],
    python_requires='>=3.6',
    project_urls={  # Additional project links to provide more context
        'Homepage': 'https://github.com/spignelon/ShareDir',
        'Bug Tracker': 'https://github.com/spignelon/ShareDir/issues',
        'Source Code': 'https://github.com/spignelon/ShareDir/blob/main/sharedir/sharedir.py',
    },
)
