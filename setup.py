import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='azure-video-pipeline',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='Provide ability to use MS Azure services as OpenEdx video upload, processing and delivery backend.',
    long_description=README,
    url='https://github.com/raccoongang/azure-video-pipeline',
    author='raccoongang',
    author_email='info@raccoongang.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    install_requires=[
        'django>=1.8,<1.9',
        'edx-organizations'
    ]
)
