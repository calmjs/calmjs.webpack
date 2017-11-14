calmjs.webpack
==============

Package for extending the the `Calmjs framework`_ to support the usage
of `webpack`__ for the generation of deployable artifacts from
JavaScript source code provided by Python packages in conjunction with
standard JavaScript or `Node.js`_ packages sourced from |npm|_ or other
similar package repositories.

.. __: https://webpack.js.org/
.. image:: https://travis-ci.org/calmjs/calmjs.webpack.svg?branch=master
    :target: https://travis-ci.org/calmjs/calmjs.webpack
.. image:: https://ci.appveyor.com/api/projects/status/327fghy5uhnhplf5/branch/master?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-webpack/branch/master
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.webpack/badge.svg?branch=master
    :target: https://coveralls.io/github/calmjs/calmjs.webpack?branch=master

.. |npm| replace:: ``npm``
.. |webpack| replace:: ``webpack``
.. _Calmjs framework: https://pypi.python.org/pypi/calmjs
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
integration with |npm| by default.

The outcome is that a project is typically forcibly split into two
completely separate projects, or a single project has two separate
deployment systems that do not necessarily talk to each other.  This
results in issues including, but not limited to, end-users having
difficulties reproducing the build, or that the deployment process of
the deployable client-side artifacts being tightly coupled to the
underlying source repository for the package.  Ultimately, this leaves
the users of the backend language not having a way to convey these
information across package boundaries for reuse by other downstream
packages, for instance, to provide methodologies for development of
extensions and plugins.

This kind of self-contained behavior also plagues |webpack|_, where
each `Node.js`_ package provide the resulting artifact, but not
necessarily the methods that went into generating them.  Sure, most
typical use case can be addressed by simply specifying the entry point,
however for systems that offer unspecified plugin-based systems this
quickly becomes problematic, since webpack requires all imports be
known at build time.  This makes arbitrary extensions very difficult
to implement without a separate system that acts as an overseer for
what modules names are available and where they might be.

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
JavaScript code they provide, and also the system that allow Python
packages to declare which of their modules export JavaScript sources
that can be reused.

The utility included with |calmjs.webpack| provide the means to consume
those declarations, treating the JavaScript files as both source and
compilation target, with the final deployable artifact(s) being produced
through |webpack| from the |webpack|_ package.

Currently, the source files could be written in any format as understood
by webpack, though currently only standard ES5 is understood.  For
dynamic imports to work, both the AMD and CommonJS import invocation
methods (i.e. via ``require``) are understood and this will be
transpiled into the common Calmjs helper module that will be injected
into the affected webpack artifacts.  (XXX to be implemented)

The resulting sources will be placed in a build directory, along with
all the declared bundled sources acquired from the Node.js package
managers or repositories, plus the (optionally) generated module.  A
webpack configuration file will then be generated that will include all
the relevant sources as selected to enable the generation of
the final artifact file through |wepack|.  These can then be deployed to
the appropriate environment, or the whole above process can be included
as part of the functionality of the Python backend at hand.

Ultimately, the goal of |webpack| is to ease the integration and
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
installation section for details.  (XXX to be completed)


Installation
------------

It is recommended that the local environment already have Node.js and
|npm| installed at the very minimum to enable the installation of
|webpack|, if it hasn't already been installed and available.  Also,
the version of Python must be either 2.7 or 3.3+; PyPy is supported,
with PyPy3 version 5.2.0-alpha1 must be used due to a upstream package
failing to function in the currently stable PyPy3 version 2.4. (XXX TBC)

To install |calmjs.webpack| into a given Python environment, it may be
installed via the git repo through this command (XXX correct when done)

.. code:: sh

    $ pip install calmjs
    $ pip install -e git+https://github.com/calmjs/calmjs.webpack.git#egg=calmjs.webpack

If a local installation of webpack into the current directory is
desired, it can be done through |calmjs| with the following command:

.. code:: sh

    $ calmjs npm --install calmjs.webpack

Which does the equivalent of ``npm install webpack``; while this does
not seem immediately advantageous, other Python packages that declared
their dependencies for specific sets of tool can be invoked like so, and
to follow through on that.  As an example, ``example.package`` may
declare dependencies on RequireJS through |npm| plus a number of other
packages available through |webpack|, the process then simply become
this:

.. code:: sh

    $ calmjs npm --install example.package

All standard JavaScript and Node.js dependencies for ``example.package``
will now be installed into the current directory through the relevant
tools.  This process will also install all the other dependencies
through |npm| or |webpack| that other Python packages depended on by
``example.package`` have declared.  For more usage please refer to
further down this document or the documentation for |calmjs|_.

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

As |calmjs| is declared as both a namespace and a package, mixing
installation methods as described above when installing with other
|calmjs| packages may result in the module importer being unable to look
up the target module.  While this normally will not affect end users,
provided they use the same, standard installation method (i.e. wheel),
for developers it can be troublesome.  To resolve this, either stick to
the same installation method for all packages (i.e. ``python setup.py
develop``), or import a module from the main |calmjs| package.  Here
is an example run:

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
wheels acquired through ``pip``).

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
tests will be skipped.  To avoid this, either install that package
separately, or install |calmjs.webpack| using its extras dependencies
declaration like so (XXX only when released):

.. code:: sh

    $ pip install calmjs.webpack[dev]


Usage
-----

XXX none of these is currently implemented

Any exposed JavaScript code through the ``calmjs.module`` registry will
be picked up and compiled into a working RequireJS artifact.  For
details on how the calmjs registry system works please refer to the
README included with the |calmjs|_ project.

For example, given the following entry points for that registry defined
by a package named ``example``:

.. code:: ini

    [calmjs.module]
    example.lib = example.lib
    example.app = example.app

While the import locations declared looks exactly like a Python module
(as per the rules of a Python entry point), the ``calmjs.module``
registry will present them using the es6 style import paths (i.e.
``'example/lib'`` and ``'example/app'``), so users of that need those
JavaScript modules to be sure they ``require`` those strings.  Also,
the default extractor will extract all source files within those
directories.  Also, as a consequence of how the imports are done, it is
recommended that no relative imports be used.

To extract all JavaScript modules declared within Python packages
through this registry can be done like so through the ``calmjs webpack``
build tool, which would extract all the relevant sources, create a
temporary build directory, generate the build manifest and invoke
``webpack`` on that file.  An example run:

.. code:: sh

    $ calmjs webpack example

XXX 

As the build process used by |calmjs.webpack| is done in a separate
build directory, all imports through the Node.js module system must be
declared as ``extras_calmjs``.  For instance, if ``example/app/index``
need to use the ``jquery`` and ``underscore`` modules like so:

.. code:: JavaScript

    var $ = require('jquery'),
        _ = require('underscore');

It will need to declare the target location sourced from |npm| plus the
package_json for the dependencies, it will need to declare this in its
``setup.py``:

.. code:: Python

    setup(
        # ...
        package_json={
            "dependencies": {
                "jquery": "~3.1.0",
                "underscore": "~1.8.0",
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
it can be used from within the environment.  ``calmjs npm --install``
can now be invoked to install the |npm| dependencies into the current
directory; to permit |calmjs.webpack| to find the required files sourced
from |npm| to put into the build directory for ``r.js`` to locate them.

The resulting calmjs run may then end up looking something like this:

.. code:: sh

    $ calmjs webpack example

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

Do note that the package referenced by the handler that provides the
actual webpack loader must be available, otherwise the build will fail.

Troubleshooting
---------------

The following are some known issues with regards to this package and its
integration with other Python/Node.js packages.

UserWarning: Unknown distribution option:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During setup and installation using the development method, if this
warning message is shown, please ensure the egg metadata is correctly
generated by running ``python setup.py egg_info`` in the source
directory, as the package |calmjs| was not available when the setup
script was initially executed.


Contribute
----------

- Issue Tracker: https://github.com/calmjs/calmjs.webpack/issues
- Source Code: https://github.com/calmjs/calmjs.webpack


Legal
-----

The |calmjs.webpack| package is part of the calmjs project.

The calmjs project is copyright (c) 2016 Auckland Bioengineering
Institute, University of Auckland.  |calmjs.webpack| is licensed under
the terms of the GPLv2 or later.
