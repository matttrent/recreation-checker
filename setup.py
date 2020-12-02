from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='recreation',
   version='1.0',
   description='A useful module',
   license="MIT",
   long_description=long_description,
   author='Matthew Trentacoste',
   author_email='web+git@matttrent.com',
   url="https://github.com/matttrent/recreation-gov-campsite-checker",
   packages=['recreation'],  #same as name
   # external packages as dependencies
   install_requires='Click fake-useragent python-dateutil requests'.split(), 
   scripts=[
            'scripts/camping.py',
           ]
)
