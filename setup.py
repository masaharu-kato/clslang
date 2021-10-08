import os
from setuptools import setup, find_packages

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

setup(
    name='clslang',
    version='0.1.0',
    url='https://github.com/masaharu-kato/clslang',
    author='Masaharu Kato',
    author_email='fudai.mk@gmail.com',
    description='Classful Language Parser',
    packages=['clslang'],
    package_dir={'': 'src'},
    install_requires=[
    ],
)
