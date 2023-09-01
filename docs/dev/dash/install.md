# Dash development environment installation

* Installer Node.js
* Installer l'environnement de développement

```bash
    $ > pip install cookiecutter
    $ > pip install virtualenv
    $ > export NODE_OPTIONS=--openssl-legacy-provider 
    $ > cookiecutter gh:plotly/dash-component-boilerplate
    You have downloaded /Users/brunogas/.cookiecutters/dash-component-boilerplate before. Is it okay to delete and re-download it? [yes]: yes
    project_name [my dash component]: dash-websocket
    project_shortname [dash_websocket]: 
    component_name [DashWebsocket]: 
    jl_prefix []: 
    r_prefix []: 
    author_name [Enter your first and last name (For package.json)]: Bruno Gas
    author_email [Enter your email (For package.json)]: bruno.gas@sorbonne-universite.fr
    github_org []: 
    description [Project Description]: Websocket for Dash
    Select use_async:
    1 - False
    2 - True
    Choose from 1, 2 [1]: 2
    Select license:
    1 - MIT License
    2 - BSD License
    3 - ISC License
    4 - Apache Software License 2.0
    5 - GNU General Public License v3
    6 - Not open source
    Choose from 1, 2, 3, 4, 5, 6 [1]: 1
    publish_on_npm [True]: False
    install_dependencies [True]: True
```

Créer le dépot Git puis :

```bash 
    $ > cd dash_websocket
    $ > git init --initial-branch=main
    $ > git remote add origin https://gitlabsu.sorbonne-universite.fr/megamicros/tools/dash_websocket.git
    $ > git add .
    $ > git commit -m "Initial commit"
    $ > git push -u origin main
```

Tester:

```bash
    $ > cd dash_websocket
    $ > pip install dash
    $ > python usage.py
```

Visit http://localhost:8050 in your web browser

## Copie locale du dépôt

Lorsque vous souhaitez installer une nouvelle copie du dépôt sur votre orf-dinateur (exemple pour le projet `dash_websocket`):

* clônez le dépôt: `git clone https://gitlabsu.sorbonne-universite.fr/megamicros/tools/dash_websocket.git`
* installez les packages npm: `cd dash_websocket && npm install`

## Project structure

```
- project_shortname         # Root of the project
- project_shortname         # The python package, output folder for the bundles/classes.
- src                       # The javascript source directory for the components.
    - lib
        - components        # Where to put the react component classes.
    - demo
        - App.js            # A sample react demo, only use for quick tests.
        - index.js          # A reactDOM entry point for the demo App.
    - index.js              # The index for the components exported by the bundle.
- tests                     #
    - requirements.txt      # python requirements for testing.
    - test_usage.py         # Runs `usage.py` as a pytest integration test.
- package.json              # npm package info and build commands.
- setup.py                  # Python package info
- requirements.txt          # Python requirements for building the components and running usage.py
- usage.py                  # Sample Python dash app to run the custom component.
- webpack.config.js         # The webpack configs used to generate the bundles.
- webpack.serve.config.js   # webpack configs to run the demo.
- MANIFEST.in               # Contains a list of files to include in the Python package.
- LICENSE                   # License info
```

## Build the project

The NPM part:

```bash
$ > npm run build:js        # generate the JavaScript bundle project_shortname.min.js
$ > npm run build:backends  # generate the Python, R and Julia class files for the components.
$ > npm run build           # generate everything: the JavaScript bundles and the Python, R and Julia class files.
```

The python part:

```bash
$ > python setup.py sdis
```

## Install the component from local git

```bash
$ > pip install git+file:///path_to_git_repos
```

## Release

Change the version number in the file `package.json`, then re-compile the new version, push and upgrade:

```bash
$ > npm run build
$ > python setup.py sdist bdist_wheel
$ > git add .
$ > git commit -m "new release..."
$ > git push
```

On your application:

```bash
$ > pip install git+file:///path_to_git_repos --upgrade
```




# Documentation

* [Writing Your Own Components](https://dash.plotly.com/plugins)
* [Dash Component Boilerplate](https://github.com/plotly/dash-component-boilerplate)
* [React for python developpers](https://dash.plotly.com/react-for-python-developers#cookiecutter-boilerplate)
