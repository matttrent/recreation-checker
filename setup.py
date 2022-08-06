from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='recreation',
   version='2.0',
   description='A recreation.gov campground and permit API',
   license="MIT",
   long_description=long_description,
   author='Matthew Trentacoste',
   author_email='web+git@matttrent.com',
   url="https://github.com/matttrent/recreation-gov-campsite-checker",
   packages=['recreation'],  #same as name
   # external packages as dependencies
   install_requires=[
        "backoff>=2.1.2",
        "api-client-pydantic>=2.2.0",
        "colorama==0.4.5",
        "fake-useragent==0.1.11",
        "rich>=12.5.1",
        "shellingham>=1.4.0",
        "typer>=0.6.1",
   ], 
   scripts=[
        'scripts/camping.py',
    ],
)
