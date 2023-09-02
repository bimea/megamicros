# Writing documentation

!!! Warning
    Please make attention about the first paragraph which is not intended to write or contribute to documention but to deal with the first installation of the documentation.

## Megamicros documentation installation

The documention has to be installed in the root directory of the *megamicros* package.
Once your virtual environment is created (unless it is already installed), install the *mkdoc* packages and setup them:

```bash
    > cd megamicros
    > virtualenv venv
    > source venv/bin/activate
    (venv) > pip install mkdocs "mkdocstrings[python]" mkdocs-material plantuml_markdown
```

Create the following *javascript* file ``javascript/mathjax.js`` for latex suport:

```javascript
// javascript/mathjax.js
window.MathJax = {
    tex: {
      inlineMath: [["\\(", "\\)"]],
      displayMath: [["\\[", "\\]"]],
      processEscapes: true,
      processEnvironments: true
    },
    options: {
      ignoreHtmlClass: ".*|",
      processHtmlClass: "arithmatex"
    }
  };
  
  document$.subscribe(() => { 
    MathJax.typesetPromise()
  })
```

Then complete the ``mkdocs.yml`` generated file with your owns elements.
Basically:

```yaml
# Site config
site_name: Megamicros documentation
site_author: Bruno Gas
site_url: http://readthedoc.biimea.io

# Copyright
copyright: Copyright &copy; 2022 - 2023 Bruno Gas - Sorbonne Université

# Repository
repo_name: megamicros
repo_url: https://github.com/bimea/megamicros.git
edit_uri: edit/develop/docs/mkdocs/docs

# navigation
nav:
    #...


# Extensions
markdown_extensions:
  - abbr
  - admonition
  - attr_list
  - def_list
  - codehilite:
      guess_lang: false
  - footnotes
  - md_in_html
  - plantuml_markdown:
      format: svg
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.betterem:
      smart_enable: all
  - pymdownx.caret
  - pymdownx.critic
  - pymdownx.details
  - pymdownx.emoji:
      emoji_index: !!python/name:materialx.emoji.twemoji
      emoji_generator: !!python/name:materialx.emoji.to_svg
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.magiclink
  - pymdownx.mark
  - pymdownx.smartsymbols
  - pymdownx.snippets
  - pymdownx.superfences
  - pymdownx.tasklist:
      custom_checkbox: true
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tilde
  - pymdownx.snippets:
      base_path: src
      check_paths: true
  - toc:
      permalink: true

# Javascripts extensions
extra_javascript:
  - javascripts/mathjax.js
  - https://polyfill.io/v3/polyfill.min.js?features=es6
  - https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js


# Doc theme
theme: 
  name: material
  language: en
  features:
    - content.code.copy
    - content.code.select
    - navigation.instant
    - navigation.tracking
    - navigation.tabs
    - navigation.indexes
    - navigation.top
    - content.tabs.link
  font:
    text: Roboto
    code: JetBrains Mono
  palette:
    - media: '(prefers-color-scheme: light)'
      scheme: slate
      #primary: indigo
      #accent: indigo
      primary: blue
      accent: light-blue
      toggle:
        icon: material/brightness-4
        name: Switch to dark mode
    - media: '(prefers-color-scheme: dark)'
      scheme: default
      #primary: indigo
      #accent: indigo
      primary: blue
      accent: light-blue
      toggle:
        icon: material/brightness-7
        name: Switch to light mode
```

Once you’ve adapted the settings file like this, you can take a look at the current state of your boilerplate documentation by building the site:

```bash
    (venv) > mkdocs serve 
```

As soon as your terminal tells you that it’s serving the documentation on your localhost, as shown above, you can view it in your browser.

The information printed to your terminal tells you that MkDocs is serving your documentation at ``http://127.0.0.1:8000``. Open a new browser tab pointing to that URL. You’ll see the MkDocs boilerplate index page with your custom title, styled with the *Material for MkDocs* theme (see [Build Your Python Project Documentation With MkDocs](https://realpython.com/python-project-documentation-with-mkdocs/) for more details).

Don't forget to push this work on your GitHub/GitLab repository.

The next command build a static documentation site:

```bash
    > mkdocs build
```

## Contributing

Writing documentation needs some tools:

* having access to the Github repository;
* building a python local virtual environment with mkdocs enabled.

In addition, making the doc available on the net needs:

* installing the documentation container to be used with *Docker*

## Local installation

Provided you have access to the Github directory, clone it and make a python virtual environment on your local machine (unless you have already done it):

```bash
    > git clone https://github.com/bimea/megamicros.git
    > cd megamicros
    > virtualenv venv
    > source venv/bin/activate
```

Install mkdocs package in your virtual environment:

```bash
    (venv) > pip install mkdocs "mkdocstrings[python]" mkdocs-material plantuml_markdown
```

Launch the mkdocs web server:

```bash
     (venv) > mkdocs serve
```

If you prefere using another port (default is 8000 and may be busy):

```bash
     (venv) > mkdocs serve -a localhost:9003
```

You are now ready to update the doc and see results on your web navigator.

## Set documentation on line

!!! Warning
    This part will be further reviewed by substituting the MkDocs server with a simple static site generated with MkDocs.

You can build your own documentation server using docker.
The idea is to build a container that clones or pulls the doc repository before launching the python mkdocs server at every container boot/reboot.

!!! Danger
    Note that this server install is not safe. You should use instead usual robust tools for python web servers

Here is a dockerfile example:

``` yaml
    # biimea/readthedoc:latest

    FROM ubuntu:22.04

    MAINTAINER bruno.gas@sorbonne-universite.fr

    RUN apt update
    RUN apt full-upgrade -y

    RUN apt install -y git \
        openssh-client \
        vim

    RUN apt install -y python3 \
        python3-distutils \
        python3-dev \
        python3-pip \
        python3-venv

    RUN pip install mkdocs \
        mkdocs-material \
        plantuml_markdown

    RUN mkdir -p /app

    COPY docker-entrypoint.sh /
    RUN chmod 755 /docker-entrypoint.sh

    WORKDIR /app

    EXPOSE 8000

    ENTRYPOINT /docker-entrypoint.sh
```

The ``docker-entrypoint.sh`` file should be created in the same directory as ``Dockerfile``:

```bash
    #!/bin/sh

    if [ ! -d /app/Megamicros_readthedoc ] ; then
        echo "This is a first installation: cloning Readthedoc repository..."
        cd /app && git clone https://login:password@gitlabsu.sorbonne-universite.fr/megamicros/Megamicros_readthedoc.git
        echo "done"
    else
        echo "Project already installed, updating Readthedoc repository..."
        cd /app/Megamicros_readthedoc && git pull
        echo "done"
    fi

    echo "exec mkdocs server..."
    cd /app/Megamicros_readthedoc && exec mkdocs serve -a 0.0.0.0:8000
```

You can manage the container with the ``docker-compose`` program and a services configuration file ``docker-compose.yaml`` like this one:

``` yaml

    version: '3.3'

    services:
        readthedoc:
            build: ./readthedoc 
            image: biimea/readthedoc:latest
            restart: always
            container_name: readthedoc
            ports:
                - '4180:8000'
```

Where the 4180 entry port of the server is redirected to the 8000 port of the container. Hence the following for connecting to the web doc:

```bash
    http://your_web_address:4180
```

Project directories and files:

```bash
    install_dir
        |- docker-compose.yaml
        |- readthedoc
            |- Dockerfile
            |- docker-entrypoint.sh
```

Install commands:

```bash
    $ > cd install_dir
    $ > docker-compose build readthedoc
    $ > docker-compose up readthedoc
    [Ctrl][c]
    $ > docker-compose start readthedoc
```

# Documentation

* [The Mkdocs project documentation](https://www.mkdocs.org/)
* [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
* [Build Your Python Project Documentation With MkDocs](https://realpython.com/python-project-documentation-with-mkdocs/)
