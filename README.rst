calmjs.webpack
==============

Provide the integration of |webpack|_ into a Python environment through
the `Calmjs framework`_ to facilitate the usage of JavaScript sources
included with Python packages in conjunction with Node.js packages
sourced from |npm|_ or similar package repositories, for the declaration
and production of prebuilt JavaScript artifacts with |webpack| in a
manner that allow reuse and extension by Python packages' dependants.

.. image:: https://travis-ci.org/calmjs/calmjs.webpack.svg?branch=1.0.2
    :target: https://travis-ci.org/calmjs/calmjs.webpack
.. image:: https://ci.appveyor.com/api/projects/status/327fghy5uhnhplf5/branch/1.0.2?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-webpack/branch/1.0.2
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.webpack/badge.svg?branch=1.0.2
    :target: https://coveralls.io/github/calmjs/calmjs.webpack?branch=1.0.2

.. |AMD| replace:: AMD (Asynchronous Module Definition)
.. |calmjs| replace:: ``calmjs``
.. |calmjs.dev| replace:: ``calmjs.dev``
.. |calmjs.parse| replace:: ``calmjs.parse``
.. |calmjs.webpack| replace:: ``calmjs.webpack``
.. |karma| replace:: ``karma``
.. |npm| replace:: ``npm``
.. |webpack| replace:: ``webpack``
.. _Calmjs framework: https://pypi.python.org/pypi/calmjs
.. _calmjs: https://pypi.python.org/pypi/calmjs
.. _calmjs.parse: https://pypi.python.org/pypi/calmjs.parse
.. _Node.js: https://nodejs.org/
.. _npm: https://www.npmjs.com/
.. _webpack: https://webpack.js.org/

Introduction
------------

Web applications may be created using any language as their backends,
however interactive front-end user interfaces that they may provide
ultimately rely on some form of JavaScript.  This is especially true if
associated functionalities are sourced from `Node.js`_ based package
management systems such as |npm|_.  However, backend languages that
offer their own package management system typically lack comprehensive
integration with |npm|, or integration is tightly coupled with whatever
framework that is not reusable in a more generalized manner.

A common way to address this issue is that a package may be forced to be
split into two, or at the very least a completely separate deployment
system is used, in order for the JavaScript tools to manage the front-
end facing parts.  On top of this, these separate systems do not
necessarily communicate with each other.  This results in issues such as
difficulties in building the software stack, deployments being flaky and
non-reproducible outside of the project's context, limiting reusability
of all the components at hand as the entire process is typically tightly
coupled to the underlying source repository.  Ultimately, this leaves
the users of the backend language not able to convey front end
deployment information across package boundaries for reuse by their
dependents (e.g. for other downstream packages to extend the package in
ways that promote reusability in a way that is well-tested.)

This kind of self-contained behavior also plagues |webpack|_, where each
`Node.js`_ package provide the resulting artifact, but not necessarily
the methods that went into generating them in a form that is reusable.
Sure, most typical use case for those packages can be addressed by
simply specifying the entry point, however for systems that offer
dynamic plugin-based systems this quickly becomes problematic, as
webpack requires that all imports be known at build time.  This makes
arbitrary extensions very difficult to implement without a separate
system that acts as an overseer for what modules names are available and
where they might be.

As the goal of the `Calmjs framework`_ is to allow Python packages to
expose their JavaScript code as if they are part of the |npm| managed
module system from the client side code, this package, |calmjs.webpack|,
leverages that capability to provide not only the standard invocation
method for |webpack| for Python packages, but also the ability for
downstream packages the option to generate comprehensive webpack
artifacts or standalone webpack artifacts that only contain their
specific extensions to be used in conjunction with other existing
artifacts.


Features
--------

How |calmjs.webpack| works
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Calmjs framework provides the framework to allow Python packages to
declare the dependencies they need against |npm| based packages for the
JavaScript code they provide, and also enable Python packages to expose
any JavaScript source files that they may contain in a declarative
manner.

The utility included with |calmjs.webpack| provide the means to consume
those declarations, treating the JavaScript files as both source and
compilation target, with the final deployable artifact(s) being produced
through |webpack| from the |webpack|_ package.

While the input source files made available through Python packages
could be written in any format as understood by webpack, currently only
standard ES5 is properly processed.  The reason for this is that
|calmjs.parse|_, the parser library that |calmjs.webpack| make use for
the parsing of JavaScript, currently only understand ES5, and is used
for extracting all the import statements to create the dynamic Calmjs
import system for webpack, and to also transpile the CommonJS and |AMD|
require statements to make use of this dynamic import system.

The resulting sources will be placed in a build directory, along with
all the declared bundled sources acquired from the Node.js package
managers or repositories, plus the (optionally) generated import module.
A webpack configuration file will then be generated to include all the
relevant sources as selected to enable the generation of the final
artifact file.  These can then be deployed to the appropriate
environment, or the whole above process can be included as part of the
functionality of the Python backend at hand through the API provided
through this package.

Ultimately, the goal of |calmjs.webpack| is to ease the integration and
interactions between of client-side JavaScript with server-side Python,
by simplifying the task of building, shipping and deployment of the two
set of sources in one shared package and environment.  The Calmjs
framework provides the linkage between these two environment and the
tools provided by there will assist with the setup of a common,
reproducible local Node.js environments.

Finally, for quality control, this package has integration with
|calmjs.dev|, which provides the tools needed to set up the test
environment and harnesses for running of JavaScript tests that are part
of the Python packages for the associated JavaScript code.  However,
that package is not declared as a direct dependency, as not all use
cases will require the availability of that package.  Please refer to
installation section for details.


Installation
------------

It is recommended that the local environment already have Node.js and
|npm| installed at the very minimum to enable the installation of
|webpack|, if it hasn't already been installed and available.  Also,
the version of Python must be either 2.7 or 3.3+.  Both PyPy and PyPy3
are supported, with the recommended versions being PyPy3-5.2 or greater,
although PyPy3-2.4 should work, however there may be difficulties due to
new versions of dependencies rejecting older versions of Python.

To install |calmjs.webpack| into a given Python environment, it may be
installed directly from PyPI with the following command:

.. code:: sh

    $ pip install calmjs.webpack

Installing/using webpack with calmjs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _installing webpack for calmjs:

To establish a development/build environment for a Python package with
the support for |webpack| through |calmjs.webpack| in the current
working directory, the following command may be executed:

.. code:: sh

    $ calmjs npm --install calmjs.webpack

While running ``npm install webpack`` (along with other related packages
declared by |calmjs.webpack| that it needs from |npm|) will achieve the
same effect, do note the Calmjs framework makes it possible for |npm|
dependencies to be propagated down to dependent packages; such that if a
Python package that have declared |calmjs.webpack| as a dependency
(either through ``install_requires`` or an ``extras_require`` in its
``setup.py``) may have its complete set of dependencies on |npm| be
installed using the following command (assuming the package is named
``example.package``:

.. code:: sh

    $ calmjs npm --install example.package

If the dependency on |calmjs.webpack| was declared as an extras_require
dependency under a section named |webpack|, the command will then become
the following:

.. code:: sh

    $ calmjs npm --install example.package[webpack]

If the dependencies are declared correctly, using the above command will
install all the required dependencies for the JavaScript/Node.js code
required by ``example.package`` into the current directory through
|npm|.  Note that its dependents will also gain the declared
dependencies.

For further details about how this all works can be found in the
documentation for |calmjs|_.  Otherwise, please continue to the `usage`_
section.

Alternative installation methods (advanced users)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Development is still ongoing with |calmjs.webpack|, for the latest
features and bug fixes, the development version can be installed through
git like so:

.. code:: sh

    $ pip install calmjs
    $ pip install git+https://github.com/calmjs/calmjs.webpack.git#egg=calmjs.webpack

Alternatively, the git repository can be cloned directly and execute
``python setup.py develop`` while inside the root of the source
directory.

Keep in mind that |calmjs| MUST be available before the ``setup.py``
within the |calmjs.webpack| source tree is executed, for it needs the
``package_json`` writing capabilities in |calmjs|.  Alternatively,
please execute ``python setup.py egg_info`` if any message about
``Unknown distribution option:`` is noted during the invocation of
``setup.py``.

As |calmjs| is declared as both namespace and package, there are certain
low-level setup that is required on the working Python environment to
ensure that all modules within can be located correctly.  However,
versions of ``setuptools`` earlier than `v31.0.0`__ does not create the
required package namespace declarations when a package is installed
using this development installation method when mixed with ``pip
install`` within the same namespace.  As a result, inconsistent import
failures can happen for any modules under the |calmjs| namespace.  As an
example:

.. __: https://setuptools.readthedocs.io/en/latest/history.html#v31-0-0

.. code:: python

    >>> import calmjs.webpack
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ImportError: No module named 'calmjs.webpack'
    >>> import calmjs.base
    >>> import calmjs.webpack
    >>>

If this behavior (and workaround) is undesirable, please ensure the
installation of all |calmjs| related packages follow the same method
(i.e. either ``python setup.py develop`` for all packages, or using the
wheels acquired through ``pip``), or upgrade ``setuptools`` to version
31 or greater and reinstall all affected packages.

Testing the installation
~~~~~~~~~~~~~~~~~~~~~~~~

Finally, to verify for the successful installation of |calmjs.webpack|,
the included tests may be executed through this command:

.. code:: sh

    $ python -m unittest calmjs.webpack.tests.make_suite

However, if the steps to install external Node.js dependencies to the
current directory was followed, the current directory may be specified
as the ``CALMJS_TEST_ENV`` environment variable.  Under POSIX compatible
shells this may be executed instead from within that directory:

.. code:: sh

    $ CALMJS_TEST_ENV=. python -m unittest calmjs.webpack.tests.make_suite

Do note that if the |calmjs.dev| package is unavailable, a number of
tests relating to integration with |karma| will be skipped.  To avoid
this, either install |calmjs.dev| manually, or install |calmjs.webpack|
using its extras dependencies declaration like so:

.. code:: sh

    $ pip install calmjs.webpack[dev]


Usage
-----

To generate a webpack artifact from packages that have JavaScript code
exposed through the Calmjs module registry system that are already
installed into the current environment, simply execute the following
command:

.. code:: sh

    $ calmjs webpack example.package

The following sections in this document will provide an overview on how
to enable the JavaScript module export feature for a given Python
package through the Calmjs module registry system, however a more
thorough description on this topic may be found in the README provided
by the |calmjs|_ package, under the section `Export JavaScript code from
Python packages`__.

.. __: https://pypi.python.org/pypi/calmjs/#export-javascript-code-from-python-packages


Declaring JavaScript exports for the Python package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

JavaScript code embedded within a Python package can be exposed to the
Calmjs framework through the ``calmjs.module`` registry.  For example,
given the the following entry points for that registry defined by a
package named ``example``:

.. code:: ini

    [calmjs.module]
    example = example

This is the most basic declaration that works for packages that share
the same name as the import location provided.

The following is am example for packages that have nested submodules
(called ``example.lib`` and ``example.app``):

.. code:: ini

    [calmjs.module]
    example.lib = example.lib
    example.app = example.app

While the import locations declared looks exactly like a Python module
(as per the rules of a Python entry point), the ``calmjs.module``
registry will present them using the CommonJS/ES6 style import paths
(i.e.  ``'example/lib'`` and ``'example/app'``).  Thus users that wish
to import those specific JavaScript modules will then ``require`` the
required modules prefixed by those strings.

Please also note that the default source extractor will extract all
JavaScript files within those directories.  Finally, as a consequence of
how the imports are done, it is recommended that no relative imports are
to be used.

If the package at hand does not directly declare its dependency on
|calmjs|, an explicit ``calmjs_module_registry=['calmjs.module']`` may
need to be declared in the ``setup`` function for the package to ensure
that this default module registry will be used to acquire the JavaScript
sources from.

Putting this together, the ``setup.py`` file should contain the
following:

.. code:: Python

    setup(
        name='example',
        # ... plus other declarations
        # this is recommended
        license='gpl',
        install_requires=[
            'calmjs>=3.0.0,<4',
            'calmjs.webpack>=1.0.0,<2',
            # plus other installation requirements
        ],
        # If the usage of the GPL is impossible for the project, or
        # declaring a direct dependency on calmjs packages is impossible
        # for the project for whatever other reasons (even though the
        # project itself will NOT be required to include/import ANY code
        # from the calmjs namespace), setup_requires may be used instead
        # of install_requires, and the following should also be included
        # as well:
        package_json={
            "devDependencies": {
                "webpack": "~2.6.0",
            }
        },
        calmjs_module_registry=['calmjs.module'],
        # the entry points are required to allow calmjs to pick this up
        entry_points="""
        [calmjs.module]
        example = example
        example.lib = example.lib
        example.app = example.app
        """,
    )

For the construction of the webpack artifact for the example package, it
may be done like so through the ``calmjs webpack`` build tool, which
would extract all the relevant sources, create a temporary build
directory, generate the build manifest and invoke ``webpack`` on that
file.  An example run:

.. code:: sh

    $ calmjs webpack example
    Hash: 1dbcdb61e3afb4d2a383
    Version: webpack 2.6.1
    Time: 82ms
         Asset     Size  Chunks             Chunk Names
    example.js  4.49 kB       0  [emitted]  main
       [1] /tmp/tmp7qvdjb5z/build/example/lib/core.js 51 bytes {0} [built]
           cjs require example/lib/core [2] /tmp/tmp7qvdjb5z/build/__calmjs_loader__.js 6:24-51
           cjs require example/lib/core [4] /tmp/tmp7qvdjb5z/build/example/app/index.js 1:10-37
       [2] /tmp/tmp7qvdjb5z/build/__calmjs_loader__.js 559 bytes {0} [built]
           cjs require __calmjs_loader__ [3] /tmp/tmp7qvdjb5z/build/__calmjs_bootstrap__.js 3:20-48
       [3] /tmp/tmp7qvdjb5z/build/__calmjs_bootstrap__.js 341 bytes {0} [built]
       [4] /tmp/tmp7qvdjb5z/build/example/app/index.js 74 bytes {0} [built]
           cjs require example/app/index [2] /tmp/tmp7qvdjb5z/build/__calmjs_loader__.js 7:25-53
        + 1 hidden modules

As the build process used by |calmjs.webpack| is executed in a separate
build directory, all imports through the Node.js module system must be
declared as ``extras_calmjs``, as the availability of ``node_modules``.
will not be present.  For instance, if ``example/app/index.js`` require
the usage of the ``jquery`` and ``underscore`` modules like so:

.. code:: JavaScript

    var $ = require('jquery'),
        _ = require('underscore');

It will need to declare the target location sourced from |npm| plus the
``package_json`` for the dependencies, it will need to declare this in
its ``setup.py``:

.. code:: Python

    setup(
        # ...
        package_json={
            "dependencies": {
                "jquery": "~3.1.0",
                "underscore": "~1.8.0",
            },
            "devDependencies": {
                # development dependencies from npm
            },
        },
        extras_calmjs = {
            'node_modules': {
                'jquery': 'jquery/dist/jquery.js',
                'underscore': 'underscore/underscore.js',
            },
        },
    )

Once that is done, rerun ``python setup.py egg_info`` to write the
freshly declared metadata into the package's egg-info directory, so that
it can be used from within the environment.  ``calmjs npm --install
example`` can now be invoked to install the |npm| dependencies into the
current directory; to permit |calmjs.webpack| to find the required files
sourced from |npm| to put into the build directory for ``webpack`` to
locate them.

The resulting calmjs run may then end up looking something like this:

.. code:: sh

    $ calmjs webpack example
    Hash: fa76455e8abdb96273aa
    Version: webpack 2.6.1
    Time: 332ms
         Asset    Size  Chunks                    Chunk Names
    example.js  326 kB       0  [emitted]  [big]  main
       [1] /tmp/tmposbsof05/build/example/lib/core.js 51 bytes {0} [built]
           cjs require example/lib/core [4] /tmp/tmposbsof05/build/__calmjs_loader__.js 7:24-51
           cjs require example/lib/core [6] /tmp/tmposbsof05/build/example/app/index.js 1:10-37
       [2] /tmp/tmposbsof05/build/jquery.js 268 kB {0} [built]
           cjs require jquery [4] /tmp/tmposbsof05/build/__calmjs_loader__.js 8:14-31
           cjs require jquery [6] /tmp/tmposbsof05/build/example/app/index.js 2:8-25
       [3] /tmp/tmposbsof05/build/underscore.js 52.9 kB {0} [built]
           cjs require underscore [4] /tmp/tmposbsof05/build/__calmjs_loader__.js 9:18-39
           cjs require underscore [6] /tmp/tmposbsof05/build/example/app/index.js 2:31-52
       [4] /tmp/tmposbsof05/build/__calmjs_loader__.js 633 bytes {0} [built]
           cjs require __calmjs_loader__ [5] /tmp/tmposbsof05/build/__calmjs_bootstrap__.js 3:20-48
       [5] /tmp/tmposbsof05/build/__calmjs_bootstrap__.js 341 bytes {0} [built]
       [6] /tmp/tmposbsof05/build/example/app/index.js 128 bytes {0} [built]
           cjs require example/app/index [4] /tmp/tmposbsof05/build/__calmjs_loader__.js 6:25-53
        + 1 hidden modules

Trigger test execution as part of webpack artifact building process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For testing, declare the appropriate entries to the module test registry
that accompanies the module registry for the given package, and with the
use of the |karma| runtime provided by the ``calmjs.dev`` package, the
tests may be executed as part of the webpack artifact build process.
The command is simply this:

.. code:: sh

    $ calmjs karma webpack example

Do note that both the ``devDependencies`` provided by both
``calmjs.dev`` and ``calmjs.webpack`` must be installed.  This can
easily be done by declaring the appropriate ``install_requires``, or
manually install ``calmjs.dev`` and then install the dependencies from
|npm| using ``calmjs npm -D --install calmjs.webpack[dev]``.

Dynamic module imports
~~~~~~~~~~~~~~~~~~~~~~

While |webpack| does natively support this to some extent, the support
is only implemented through direct filesystem level support.  In the
case of Calmjs, where the imports are done using identifiers on the
aliases explicitly defined in generated ``webpack.conf.js``
configuration, |webpack| is unable to resolve those aliases by default.

Instead of trying to make ``ContextReplacementPlugin`` work or writing
another webpack plugin, a surrogate ``__calmjs__`` import module is
automatically generated and included in each generated artifact such
that the dynamic imports will function as intended.  The rationale for
using this as a workaround is simply a desire to avoid possible API
changes to |webpack| as plugins of these nature will end up being
tightly coupled to |webpack|.

With the usage of a surrogate import module, the dynamic imports also
work across multiple |webpack| artifacts generated through ``calmjs
webpack``, however this is an advanced topic thus further documentation
will be required, as specific declaration/import order and various other
caveats exists that complicates real world usage (e.g. correct handling
of circular imports will always remain a non-trivial problem).

For the simple case, imagine the following JavaScript code:

.. code:: JavaScript

    var loader = function(module_name) {
        // the dynamic import
        var module = require(module_name);
        console.log(module + ' was loaded dynamically.');
    };

    var demo = loader('example/lib/core');

If the ``example/lib/core.js`` source file was exported by ``example``
package and was included in the webpack, the above dynamic import should
function without issues at all by default without further configuration.

If this dynamic import module functionality is unwanted and that no
dynamic imports are used by any JavaScript code to be included, this
feature may be disabled by the ``--disable-calmjs-compat`` flag.

Handling of Webpack loaders
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a provided JavaScript module imports a target using the inline loader
syntax, the default registry ``calmjs.webpack.loaderplugins`` will
resolve a generic handler to copy the target files.  This generic
handler supports the chaining of loaders.  If this behavior is unwanted,
a static registry is defined at ``calmjs.webpack.static.loaderplugins``
for this purpose.  If a mix of the two is needed (e.g. where some
specific loader require special handling), it is also possible to
register the specific handler to override the generic handler for that
specific loader.

So if some JavaScript code contain a require statement like:

.. code:: JavaScript

    var readme = require('text!readme.txt');

And there exists a custom Calmjs module registry that provide those
sources, the default loaderplugin handler registry will provide a
standard handler that will process this, provided the loader package is
available along with webpack on the working Node.js environment.

Testing standalone, finalized webpack artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Webpack artifacts generated using the standard ``calmjs webpack``
toolchain runtime may be tested using the ``calmjs karma`` runtime
provided by the ``calmjs.dev`` package.  Given a finalized
``example.webpack.js`` that implements the features provided by the
``example`` package, the artifact may be tested with the tests provided
by the ``example`` package using the following command:

.. code:: sh

    $ calmjs karma run \
        -t calmjs.webpack \
        --artifact=example.webpack.js \
        example

The above command invokes the standalone Karma runner using the
``calmjs.webpack`` settings to test against the ``example.webpack.js``
artifact file, using the tests provided by the ``example`` package.  The
test execution is similar to the one during the development process.

Declaring prebuilt webpack artifacts for Python packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, to complete the Python package deployment story, the process
should include the automatic generation and inclusion of the JavaScript
artifacts in the resulting Python wheel.  This can be achieved by
specifying an entry in the ``calmjs.artifacts`` registry, with the key
being the filename of the artifact and the value being the import
location to a builder.  A default builder function provided at
``calmjs.webpack.artifact:complete_webpack`` will enable the generation
of a complete webpack artifact for the Python package.  The builder
``calmjs.webpack.artifact:optimize_webpack`` will do the same, but with
the optimize options enabled (currently only the minimize output is
supported).

For example, a configuration that contains both forms might look like
so:

.. code:: ini

    [calmjs.artifacts]
    example.webpack.js = calmjs.webpack.artifact:complete_webpack
    example.webpack.min.js = calmjs.webpack.artifact:optimize_webpack

Once those entry points are added to ``setup.py`` and the package
metadata is regenerated using ``setup.py egg_info``, running ``calmjs
artifact build example.package`` will make use of the webpack toolchain
and build the artifact at ``example.webpack.js`` inside the
``calmjs_artifacts`` directory within the package metadata directory for
``example.package``.  Alternatively, for solution more integrated with
``setuptools``, the ``setup`` function in ``setup.py`` should also
enable the ``build_calmjs_artifacts`` flag such that ``setup.py build``
will also trigger the building process.  This is useful for
automatically generating and including the artifact as part of the wheel
building process.  Consider this ``setup.py``:

.. code:: Python

    setup(
        name='example.package',
        # ... other required fields truncated
        build_calmjs_artifacts=True,
        entry_points="""
        # ... other entry points truncated
        [calmjs.module]
        example.package = example.package

        [calmjs.artifacts]
        example.webpack.js = calmjs.webpack.artifact:complete_webpack
        example.webpack.min.js = calmjs.webpack.artifact:optimize_webpack
        """,
    )

Building the wheel using ``setup.py`` may result in something like this.
Note that the execution of |webpack| was part of the process and that
the metadata (egg-info) directory was then built into the wheel.

.. code::

    $ python setup.py bdist_wheel
    running bdist_wheel
    running build
    ...
    running build_calmjs_artifacts
    automatically picked registries ['calmjs.module'] for sourcepaths
    using loaderplugin registry 'calmjs.webpack.loaderplugins'
    using calmjs bootstrap; webpack.output.library set to '__calmjs__'
    ...
    Version: webpack 2.6.1
    Time: 240ms
                 Asset    Size  Chunks                    Chunk Names
    example.webpack.js   10 kB       0  [emitted]  [big]  main
    ...
    running install_egg_info
    Copying src/example.package.egg-info to build/.../wheel/example.package...
    running install_scripts
    creating build/.../wheel/example.package-1.0.dist-info/WHEEL

For testing the package artifact, the following entry point should also
be specified under the ``calmjs.artifacts.tests`` registry, such that
running ``calmjs artifact karma example.package`` will execute the
JavaScript tests declared by ``example.package`` against the artifacts
that were declared in ``calmjs.artifacts``.

.. code:: ini

    [calmjs.artifacts.tests]
    example.webpack.js = calmjs.webpack.artifact:test_complete_webpack
    example.webpack.min.js = calmjs.webpack.artifact:test_complete_webpack

Note that the same ``test_complete_webpack`` test builder will be able
to test the optimize_webpack artifact also.


Troubleshooting
---------------

The following are some known issues with regards to this package and its
integration with other Python/Node.js packages.

CRITICAL calmjs.runtime WebpackRuntimeError: unable to locate 'webpack'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means the current Node.js environment is missing the |webpack|
package from |npm|; either install it manually with it or through
|calmjs| on this package.  If a given Python package is required to use
webpack to generate the package, its ``package_json`` should declare
that, or declare dependency on ``calmjs.webpack``.

CRITICAL calmjs.runtime WebpackExitError: webpack terminated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This can be caused by a variety of reasons; it can be due to invalid
syntax in the provided JavaScript code, or that the configuration not
containing enough information for |webpack| to correctly execute, or
that specific ``calmjs webpack`` flags have been enabled in a way that
is incompatible with |webpack|.  To extract further information about
the error, the same |calmjs| command may be executed once more with the
``--verbose`` and/or ``--debug`` flag enabled for extra log message
which may reveal further information about the nature of the error, or
that the full traceback may provide further information.  Detailed
information must be included for the filing of bug reports on the
`issue tracker`_.

UserWarning: Unknown distribution option:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During setup and installation using the development method, if this
warning message is shown, please ensure the egg metadata is correctly
generated by running ``python setup.py egg_info`` in the source
directory, as the package |calmjs| was not available when the setup
script was initially executed.

WARNING could not locate 'package.json' for the npm package '???-loader'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The warning message is triggered when there was an attempt to use a
webpack loader without the appropriate loader module installed into the
working Node.js environment.  As a quick workaround to the webpack
artifact build issue, the missing package installation command may be
attempted, however the correct solution is for that package to declare
the correct loader package as the dependency in ``package_json``.


Contribute
----------

.. _issue tracker:

- Issue Tracker: https://github.com/calmjs/calmjs.webpack/issues
- Source Code: https://github.com/calmjs/calmjs.webpack


Legal
-----

The |calmjs.webpack| package is part of the calmjs project.

The calmjs project is copyright (c) 2016 Auckland Bioengineering
Institute, University of Auckland.  |calmjs.webpack| is licensed under
the terms of the GPLv2 or later.
