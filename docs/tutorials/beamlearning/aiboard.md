
# Using Aiboard for data labeling

*AiBoard* is a Megamicros application that lets you create a database of labeled signals from raw sound signals.

## Install it

!!! Warning
    *megamicros* and *dash-websocket* packages are private packages.
    Please see [downloading from private repository section](../megamicros/get_started.md) for downloading them.

For *AiBoard* to work, you need to have installed the following libraries: *megamicros*, *dash* and some of its components, *plotly* for signal tracing and various other libraries:

```bash
    $ > cd your_project_path
    $ > virtualenv venv
    $ > source venv/bin/activate
    (venv) $ > pip install --upgrade pip
    (venv) $ > pip install scipy dash dash-bootstrap-components plotly pandas requests
    (venv) $ > pip install megamicros dash-websocket
```

Note that ``dash-websocket`` is a *Megamicros* component. As such it should be loaded from the *Megamicros* repository.

Start *AiBoard*. A web server is launched that you can target at ``http://localhost:8050``:

```bash
    $ > megamicros-aiboard
    2023-09-26 14:45:30,255 [INFO]: Starting Aiboard...
    2023-09-26 14:45:30,255 [INFO]:  .Set verbose level to [debug]
    Dash is running on http://127.0.0.1:8050/
```

If you have downloaded *Megamicros* sources from the GitHub repository you can access the *AiBoard* application from the source:

```bash
    $ > python src/megamicros/aiboard/main.py
    2023-09-26 14:45:30,255 [INFO]: Starting Aiboard...
    2023-09-26 14:45:30,255 [INFO]:  .Set verbose level to [debug]
    Dash is running on http://127.0.0.1:8050/
```

## Aiboard user manual

Before use, you must configure *AiBoard* by connecting the application to an *Aidb* database.
Then log in, and access the following pages of the application:

* *Configuration*: the login and configuration page;
* *Labels*: the label definition page;
* *Labeling*: the data labeling page;
* *Dataset*: the page for building downloadable learning databases.

### Configuration

### Labels

### Etiquetage

### Dataset

On this page you can list all segmented bases created, create new bases, modify and delete bases.
You can also view the characteristics of a base and listen to extracts.
Finally, you can download bases.

