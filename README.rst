calmjs.webpack
==============

Package for extending the the `Calmjs framework`_ to support the usage
of |webpack|_ for the generation of deployable artifacts from
JavaScript source code provided by Python packages in conjunction with
standard JavaScript or `Node.js`_
similar package repositories.

.. image:: https://travis-ci.org/calmjs/calmjs.webpack.svg?branch=master
    :target: https://travis-ci.org/calmjs/calmjs.webpack
.. image:: https://ci.appveyor.com/api/projects/status/327fghy5uhnhplf5/branch/master?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-webpack/branch/master
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.webpack/badge.svg?branch=master
    :target: https://coveralls.io/github/calmjs/calmjs.webpack?branch=master

.. |calmjs| replace:: ``calmjs``
.. |calmjs.dev| replace:: ``calmjs.dev``
.. |calmjs.webpack| replace:: ``calmjs.webpack``
.. |npm| replace:: ``npm``
.. |webpack| replace:: ``webpack``
.. _Calmjs framework: https://pypi.python.org/pypi/calmjs
.. _calmjs: https://pypi.python.org/pypi/calmjs
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
could be written in any format as understood by webpack,
currently only standard ES5 is understood.  The reason for this is that
|calmjs.parse|_, the parser library that |calmjs.webpack| make use for
the parsing of JavaScript, currently only understand ES5, and is used
for extracting all the import statements to create the dynamic Calmjs
import system for webpack, and to also transpile the CommonJS and AMD
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
to follow through on that.  As an example, a given package (say
``demo.package``) may declare dependencies on |webpack| along with a
number of other packages that they require through |npm|, the process
then simply become this:

.. code:: sh

    $ calmjs npm --install demo.package

All standard JavaScript and Node.js dependencies for ``demo.package``
will now be installed into the current directory through the relevant
tools.  This process will also install all the other dependencies
through |npm| or |webpack| that other Python packages depended on by
``demo.package`` have declared.  Most importantly, dependents of
``demo.package`` will also gain those requirements available via |npm|.

For more usage please continue reading through this document or consult
the documentation for |calmjs|_.

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
as typically only the standard installation method (i.e. wheel) will be
used, for developers it can be troublesome.  To resolve this, reinstall
all packages using the same installation method (i.e. ``python setup.py
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

To generate a webpack artifact from packages that have JavaScript code
exposed through the Calmjs module registry system that are already
installed into the current environment, simply execute the following
command:

.. code:: sh

    $ calmjs webpack some.package

For further information about the inner workings of the registry system,
please refer to the README provided by the |calmjs|_ package, under the
section "Export JavaScript code from Python packages"

Declaring JavaScript exports for Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
registry will present them using the CommonJS style import paths (i.e.
``'example/lib'`` and ``'example/app'``), so users of that need those
JavaScript modules to be sure they ``require`` those strings.

Please also note that the default source extractor will extract all
JavaScript files within those directories.  Finally, as a consequence of
how the imports are done, it is recommended that no relative imports are
to be used.

If the package at hand does not directly declare its dependency on
|calmjs|, an explicit ``calmjs_module_registry=['calmjs.module']`` may
need to be declared in the ``setup`` function for the package to ensure
that this source registry will be used to acquire the source from.

Putting this together, the ``setup.py`` file should contain the
following:

.. code:: Python

    setup(
        name='example',
        # ... plus other declarations
        # this is recommended
        install_requires=[
            'calmjs>=3.0.0',
        ],
        # if the above is omitted, ensure this is included
        calmjs_module_registry=['calmjs.module'],
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
