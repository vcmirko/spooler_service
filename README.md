# The spooler service

The main principle of the application is to create flows.  A flow is a set of steps that will be executed in order.  

TODO : a proper name, I like the idea of an octopus, grabbing and passing data with it's tentacles.

```
├── README.md
├── main.py
├── flow_processor/
│   ├── __init__.py
│   ├── api.py
│   ├── flow_scheduler.py
|   ├── flow.py
│   ├── locks.py
│   ├── factory.py
|   ├── steps.py
│   ├── config.py
│   ├── utils.py
│   ├── steps/
│   │   ├── file_step.py
│   │   ├── rest_step.py
│   │   ├── jq_step.py
│   │   ├── jinja_step.py
│   │   ├── flow_step.py
│   │   ├── flow_loop_step.py
│   │   └── jira_fields_step.py
├── data/
│   ├── config.yml
│   ├── secrets.yml
│   ├── flows/
│   │   ├── flow1.yml 
|   │   ├── flow2.yml
│   ├── locks/
│   │   ├── flow1.lock
│   │   ├── flow2.lock
│   ├── logs/
│   │   ├── spooler_service.log
|   ├── templates/
│   │   ├── template1.j2
│   │   ├── template2.j2
│   ├── ... other data files (input, output, etc.)
```

# environment variables

The application uses several environment variables to configure the application.  These are the main ones:

Note that they are all optional.  
The DATA_PATH is the root path for all custom files, including the config, secrets, flows, locks, logs, templates and other data files.  The default is `data/`.  The application will create the directories if they do not exist.  But feel free to override them.  The application will use the environment variables to create the paths.


- DATA_PATH: Path to the data directory.  
  default: `data/`
- LOCK_PATH: Path to the directory for lock files.  
  default: `data/locks/`
- LOG_PATH: Path to the directory for log files.  
  default: `data/logs/`
- FLOWS_PATH: Path to the directory for flow files.  
  default: `data/flows/`
- TEMPLATES_PATH: Path to the directory for template files.  
  default: `data/templates/`
- SECRETS_PATH: Path to the secrets file.  
  default: `data/secrets.yml`
- CONFIG_FILE: Path to the configuration file.  
  default: `data/config.yml`
- API_PORT: Port for the API server.   
  default: `5000`
- API_PROTOCOL: Protocols for the API server (comma-separated).  
  default: `http`
- API_TOKEN: Token for API authentication.  
  default: `default_token`



# security


we will be using several types of secrets, username/password, tokens... 
these could be hardcoded in the secrets config file, or could be grabbed from hashicorp vault.

`secrets.yml`

```yaml
- name: secretX
  type: credential
  username: xxx
  password: xxx
- name: secretY
  type: token
  token: yyy
# TODO grab from hashicorp vault
```

`API_TOKEN`   

The service has a rest api wrapped around the service.   the API_TOKEN environment variable will be used to authenticate the requests.  it's a bearer token (Bearer <token>).

TODO : transform the app into a full blown enterprise application with a database for users, roles, ldap, MFA, request tokens, etc.  Redis to store the tokens, etc.  This is a long term goal, for now we will use a simple token.

# entry script


The `main.py` was originally the main entry, but after adding the api, the logic has been moved to the api.py file, because the api.py file will become the main entry point.  The `main.py` is a wrapper around `lib.prow_processor.api.py` for testing.  

For now the api uses app.run, but in the future it will be moved to a wsgi server (gunicorn, uWSGI, etc.) for production use.  This will require the logging to be moved to the app level.  For now I have been testing on my laptop (windows) so gunicorn is not an option.  Looking for some python magicians to help me with this.

# flow_processor
  
The flow_processor is the main module of the application.  It will be used to create the flows and steps.  It will also be used to run the flows and steps.  The flow_processor will be used by the `api.py` file to run the flows.

# the flow class

The flow class is quite simple.  It has a name, an optional schedule property (`cron` or `every_seconds`) and a list of steps.  

The flow instance has a few properties:

- _data: a dict that will hold the data during the flow
- _steps: a list of steps that will be executed in order

# the step class

The step class is the main class for the steps.  It has some generic properties that will be used by all steps. (name, type, when, ...).
Each step handles data in some form (load, read, transform, write, send).  
We use the `factory.py` to create the steps.  Currently these are the steps that are implemented:

- FileStep: a step that will read from or write to a file
- RestStep: a step that will call a rest api (GET, POST, PUT, DELETE, PATCH)
- JqStep: a step that will use jq to transform the data
- JinjaStep: a step that will use jinja2 to transform the data
- FlowStep: a step that will call another flow
- FlowLoopStep: a step that will call another flow in a loop
- JiraNamesMergeStep: a custom step that reformats the fields from Jira result, merging the names/labels.

Some ideas for future steps:
- SwitchStep: a step that will switch the data (if/else) or (match/case)
- DatabaseStep: a step that will read from or write to a database
- KafkaStep: a step that will read from or write to a kafka topic
- S3Step: a step that will read from or write to an S3 bucket
- RedisStep: a step that will read from or write to a redis database
- EmailStep: a step that will send an email

Each step has a `result_key` property that will be used to store the result of the step in the `_data` property.  
Each step also has a custom property (file,rest, jq, ...) which hold the typical properties for that step.  For example, the `FileStep` has a `path` property, the `RestStep` has a `uri` property, etc.  Some of these steps will have a `data_key` property which will be the input payload for that step.  
All steps can have `jq_expression` (json query) property that can do quick final transformation on the data.

Common properties for all steps:

- name: the name of the step
- type: the type of the step (file, rest, jq, ...)
- when: a condition that will be used to execute the step (if/else)
- result_key: the key that will be used to store the result of the step in the `_data` property
- ignore_errors: a list of regex patterns that will be used to ignore errors in the step, based on a string representation of the error.  This is useful for steps that can fail, but we want to ignore the error and continue the flow.
- jq_expression: a jq expression that will be used to transform the data

## The file step
The file step is a step that will read from or write to a file.  

file:
- path: the path to the file
  note: allows jinja2 templating
  note: relative to the DATA_PATH
- mode: the mode of the file (read, write, append)
  default: read
- type: the type of the file (json, yaml)
- data_key: the key that will be used to grab the data from the `_data` property to write to the file.

## The rest step
The rest step is a step that will call a rest api (GET, POST, PUT, DELETE, PATCH).

rest:
- uri: the uri of the rest api
  note: allows jinja2 templating
- method: the method of the rest api (GET, POST, PUT, DELETE, PATCH)
  default: GET
- headers: the headers of the rest api (json)
- body: the body of the rest api (json)
- data_key: the key that will be used to grab the data from the `_data` property to send to the rest api.  The `data_key` is higher in the hierarchy than the `body` property. 

## The jq step
The jq step is a step that will use jq to transform the data.

jq:
- expression: the jq expression that will be used to transform the data
- data_key: the key that will be used to grab the data from the `_data` property to transform.

## The jinja step
The jinja step is a step that will use jinja2 to transform the data.

jinja:
- path: the jinja2 template that will be used to transform the data
  note: relative to the TEMPLATES_PATH
- data_key: the key that will be used to grab the data from the `_data` property to transform.
- parse: optionally parse the data as json or yaml
  default: no parsing, just a string

## The flow step
The flow step is a step that will call another flow.  This is useful for reusing flows and creating complex flows.

flow:
- path: the path of the flow to call
  note: the flow must be relative to the FLOWS_PATH
- data_key: the key that will be used to grab the data from the `_data` property to send to the flow. 

## The flow loop step
The flow loop step is a step that will call another flow in a loop.  This is useful for reusing flows and creating complex flows.

flow_loop:
- path: the path to the flow to call
  note: the flow must be relative to the FLOWS_PATH
- data_key: the key that will be used to grab the data from the `_data` property to send to the flow.
  note: the data_key must be a list of items to loop over

## The jira names merge step
The jira names merge step is a custom step that reformats the fields from Jira results, merging the names/labels.

Note: the expand=names query must be used so Jira add the names to the result.

jira_names_merge:
- data_key: the key that will be used to grab the data from the `_data` property to transform.
- list_key: the key that will be used to grab the list of items to loop over in the results.
  default: issues

# The flow scheduler
--------------------
The flow scheduler is a simple scheduler that will run the flows based on a cron expression or every x seconds.  It will use the `schedule` library to run the flows.  The scheduler will run in a separate thread and will use the `flow_processor` to run the flows.  

## Add a flow

You can add a flow by path (relative to FLOWS_PATH).  It's will stored in the scheduler with a guid, so it can later be retrieved or removed.

The schedule will automatically search for the `autostart` property in the config file, which is a list of relative paths.  The scheduler will add the flows to the scheduler and start them.  The autostart property is optional, if not present, the scheduler will not start any flows.

Only flows with a schedule will be added.  If you want to launch a flow without a schedule, you can use the `/api/flows/launch` POST endpoint.

Using the api `/api/flows/add` POST you can add a flow to the scheduler.  The flow will be added to the scheduler and started.  The flow will be added to the scheduler with a guid, so it can later be retrieved or removed.  

```
{
  "path": "flow1.yml"
}
```

## Remove a flow

Use the api `/api/flows/{flow_id}` DELETE to remove a flow.  

## Get added flows

Use the api `/api/flows` to get a list of added flows.  

## Launch a flow

The `launch_flow` method will launch a flow.  The flow is launched by path (relative to FLOWS_PATH).  

## Get locks

To make sure that the flows are not running at the same time, we will use locks.  The locks are stored in the `LOCK_PATH` directory.  The locks are created by the `flow_processor` and are removed when the flow is finished.  There is no timeout on the locks.  If the application should be terminated, the locks will be removed at first start.  

Use the api `/api/locks` to get the list of locks.  

## Remove lock

Use the api `/api/locks/{flow_name}` DELETE to remove a lock.  The lock is removed by flow_name.

## Remove all locks
Use the api `/api/locks` DELETE to remove all locks.  The locks are removed by flow_name.
