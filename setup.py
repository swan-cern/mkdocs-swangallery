from setuptools import setup, find_packages

# Load README contents
with open("README.md", encoding = "utf-8") as data:
    long_description = data.read()

setup(
    name="mkdocs-swangallery",
    version='0.0.5',
    url='https://github.com/swan-cern/mkdocs-swangallery',
    license='BSD',
    description='Plugin for MkDocs to genereate a SWAN Gallery',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    author='Diogo Castro',
    author_email='diogo.castro@cern.ch',
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python",
        "Topic :: Documentation",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup :: HTML"
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'mkdocs',
        'nbconvert==5.*',
        'jinja2==2.*',
        'markupsafe==1.*',
        'ipython_genutils',
        'nbformat',
        'bs4'
        ],
    entry_points={
        'mkdocs.plugins': [
            'swangallery = mkdocs_swangallery:SwanGallery',
        ]
    },
    zip_safe=False
)