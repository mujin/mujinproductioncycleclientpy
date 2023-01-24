# -*- coding: utf-8 -*-

from distutils.core import setup
from distutils.dist import Distribution

version = {}
exec(open('python/mujinproductioncycleclient/version.py').read(), version)

setup(
    distclass=Distribution,
    name='mujinproductioncycleclient',
    version=version['__version__'],
    packages=['mujinproductioncycleclient'],
    package_dir={'mujinproductioncycleclient': 'python/mujinproductioncycleclient'},
    long_description=open('README.md').read(),
    install_requires=[
        'websockets',
        'requests',
    ],
)
