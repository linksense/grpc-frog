"""A setuptools based setup module for grpc-frog"""
# !/usr/bin/env python
# -*- coding: utf-8 -*-

from codecs import open
from os import path

from setuptools import find_packages, setup

import versioneer

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open(path.join(here, 'HISTORY.md'), encoding='utf-8') as history_file:
    history = history_file.read()

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as requirements_file:
    requirements = requirements_file.read()

with open(path.join(here, 'requirements_dev.txt'), encoding='utf-8') as requirements_dev_file:
    requirements_dev = requirements_dev_file.read()

setup(
    name='grpc-frog',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="grpc_helper",
    long_description=readme + '\n\n' + history,
    author="AngusWG",
    author_email='740713651@qq.com',
    url='https://github.com/AngusWG/grpc-frog',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    package_data={"": ["proto/google/*/*.proto", ]},
    entry_points={
        'console_scripts': [
            'grpc-frog=grpc_frog.__main__:cli_run',
            'grpc_frog=grpc_frog.__main__:cli_run',
        ],
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    extras_require={'dev_require': requirements + "\n" + requirements_dev},
)
