from setuptools import setup, find_packages

version = '0.0'

classifiers = """
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)
Operating System :: OS Independent
Programming Language :: JavaScript
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Topic :: Software Development :: Build Tools
""".strip().splitlines()

package_json = {
    "dependencies": {},
    "devDependencies": {
        "webpack": "~2.6.0",
        "karma-webpack": "~2.0.0",
    }
}

long_description = (
    open('README.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(
    name='calmjs.webpack',
    version=version,
    description=(
        "Package for extending the Calmjs framework to support the usage of "
        "webpack for the generation of deployable artifacts from "
        "JavaScript source code provided by Python packages in "
        "conjunction with standard JavaScript or Node.js packages sourced "
        "from npm or other similar package repositories."
    ),
    long_description=long_description,
    classifiers=classifiers,
    keywords='',
    author='Tommy Yu',
    author_email='tommy.yu@auckland.ac.nz',
    url='https://github.com/calmjs/calmjs.webpack',
    license='gpl',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['calmjs'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'calmjs>=3.0.0dev',
        'calmjs.parse',
    ],
    extras_require={
        'dev': [
            'calmjs.dev>=1.0.2,<2',
        ],
    },
    entry_points={
        'calmjs.registry': [
            'calmjs.webpack.loaderplugins'
            ' = calmjs.loaderplugin:LoaderPluginRegistry',
        ],
        'calmjs.webpack.loaderplugins': [
            'text = calmjs.webpack.loaderplugin:TextPluginHandler',
        ],
        'calmjs.runtime': [
            'webpack = calmjs.webpack.runtime:default',
        ],
        'calmjs.toolchain.advice': [
            'calmjs.dev.toolchain:KarmaToolchain = '
            'calmjs.webpack.dev:webpack_advice',
        ],
    },
    package_json=package_json,
    calmjs_module_registry=['calmjs.module'],
    test_suite="calmjs.webpack.tests.make_suite",
)
