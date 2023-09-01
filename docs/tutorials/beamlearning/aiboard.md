
# Using Aiboard for data labeling

## Install it

Get a local copy of the *AiBoard* repository, then create your Python virtual environnment and load the python modules which are needed for your system to work:

```bash
    $ > git clone git@github.com:beameo/Aiboard.git
    $ > cd Aibord
    $ > virtualenv venv
    $ > source venv/bin/activate
    (venv) $ > pip install --upgrade pip
    (venv) $ > pip install numpy scipy dash dash-bootstrap-components plotly pandas requests
```

Start *AiBoard*. A web server is launched that you can target at ``http://localhost:8050``:

```bash
    $ > python src/main.py
    2022-12-06 14:26:58,670 [INFO]: Starting Mu32aiboard...
    Dash is running on http://127.0.0.1:8050/
```

## Aiboard user manual

Avant toute utilisation, vous devez configurer *AiBoard* en connectant l'application à une base de donnée *Aidb*.
Connectez vous ensuite, puis accedez aux pages suivantes de l'application:

* *Configuration*: la page de connexion et de configuration;
* *Labels*: la page de définition les labels;
* *Etiquetage*: la page d'étiquetage des données;
* *Dataset*: la page pour construire des bases d'apprentissage téléchargeables.

### Configuration

### Labels

### Etiquetage

### Dataset

Sur cette page vous pouvez lister toutes les bases segmentées créées, créer de nouvelles bases, modifier et supprimer des bases.
Vous pouvez également visualiser les caractéristiques d'une bases et en écouter des extraits.
Vous pouvez enfin télécharger des bases.





