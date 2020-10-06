from setuptools import setup, find_packages

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup (
       name='promshell-titosanxez',
       version='0.1',
       packages=find_packages(),

       # Declare your packages' dependencies here, for eg:
       install_requires=['prompt_toolkit'],

       # Fill in these to make your Egg ready for upload to
       # PyPI
       author='titosanxez',
       author_email='',

       #summary = 'Just another Python package for the cheese shop',
       url='',
       license='',
       description='A small prompt-based application to query Prometheus for information',
       long_description='long_description',
       long_description_content_type="text/restructuredtext",

       # could also include long_description, download_url, classifiers, etc.

  
       )
