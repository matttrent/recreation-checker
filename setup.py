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
    url="https://github.com/matttrent/recreation-checker",
    packages=['recreation'],  #same as name
    # external packages as dependencies
    install_requires=[
        "api-client>=1.3,<2.0",
        "api-client-pydantic>=2.2,<3.0",
        "backoff>=2.2,<3.0",
        "click>=8.1,<9.0",
        "colorama>=0.4,<1.0",
        "fake-useragent>=1.1,<2.0",
        "pydantic>=1.10,<2.0",
        "regex>=2022.10",
        "requests>=2.28.1,<3.0",
        "responses>=0.12.3,<1.0",
        "rich>=13.0,<14.0",
        "shellingham>=1.5,<2.0",
        "tenacity>=8.1,<9.0",
        "typer>=0.7,<1.0",
        "types-click>=7.1,<8.0",
    ], 
    scripts=[
        'scripts/camping.py',
    ],
)
