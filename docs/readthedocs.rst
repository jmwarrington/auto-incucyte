Putting these docs online
=========================

This repository already contains the Sphinx source in ``docs/`` and the
Read the Docs build configuration in ``.readthedocs.yaml``.

One-time setup
--------------

1. Push the repository to GitHub.
2. Sign in at `Read the Docs Community <https://app.readthedocs.org/>`_ with
   GitHub.
3. Install or authorize the Read the Docs GitHub App for the
   ``jmwarrington/auto-incucyte`` repository.
4. In the Read the Docs dashboard, choose **Add project**.
5. Search for ``auto-incucyte``, select it, and choose **Continue**.
6. Keep ``main`` as the default branch and choose **Next**.
7. Confirm that ``.readthedocs.yaml`` exists when prompted.
8. Open the first build and confirm it finishes successfully.

Read the Docs will display the final site URL after the build. If the project
slug is ``auto-incucyte``, the normal URL is expected to be
``https://auto-incucyte.readthedocs.io/``.

Automatic updates
-----------------

When the GitHub App integration is connected, every push to GitHub can trigger a
new build. Edit an ``.rst`` file, commit it, and push; do not upload generated
HTML files.

Build locally
-------------

From the repository root:

.. code-block:: console

   python -m pip install -r docs/requirements.txt
   sphinx-build -W --keep-going -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` in a browser to inspect the result.

Add a documentation badge
-------------------------

After the Read the Docs project exists, add this near the top of ``README.md``:

.. code-block:: markdown

   [![Documentation Status](https://readthedocs.org/projects/auto-incucyte/badge/?version=latest)](https://auto-incucyte.readthedocs.io/en/latest/?badge=latest)

If Read the Docs assigns a different project slug, replace ``auto-incucyte`` in
both badge URLs.

Public versus private repositories
----------------------------------

Read the Docs Community is designed for public open-source repositories. Private
repository documentation uses Read the Docs for Business. Decide repository
visibility before importing the project.
