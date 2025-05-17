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
The **DATA_PATH** is the root path for all custom files, including the config, secrets, flows, locks, logs, templates and other data files.  The default is `data/`.  The application will create the directories if they do not exist.  But feel free to override them.  The application will use the environment variables to create the paths.
| Variable         | Description                                 | Default                |
|------------------|---------------------------------------------|------------------------|
| **DATA_PATH**    | Path to the data directory                  | `data/`                |
| **LOCK_PATH**    | Path to the directory for lock files        | `data/locks/`          |
| **LOG_PATH**     | Path to the directory for log files         | `data/logs/`           |
| **LOG_FILE_NAME** | Name of the log file                      | `spooler_service.log`  |
| **LOG_LEVEL**    | Log level for the application               | `INFO`                 |
| **FLOWS_PATH**   | Path to the directory for flow files        | `data/flows/`          |
| **TEMPLATES_PATH** | Path to the directory for template files  | `data/templates/`      |
| **SECRETS_PATH** | Path to the secrets file                    | `data/secrets.yml`     |
| **CONFIG_FILE**  | Path to the configuration file              | `data/config.yml`      |
| **API_PORT**     | Port for the API server                     | `5000`                 |
| **API_TOKEN**    | Token for API authentication                | `default_token`        |
| **HASHICORP_VAULT_TOKEN** | Token for HashiCorp Vault authentication |         |

# security

we will be using several types of secrets, username/password, tokens... 
these could be hardcoded in the secrets file, or could be grabbed from hashicorp vault.
We use a base `Secret` class, with a `scecret_factory.py` to create types of secrets.  The secrets are stored in the `secrets.yml` file.  The `hashicorp-vault` secret has 1 minute TTL, so it doesn't hit the vault too often, and requires the `HASHICORP_VAULT_TOKEN` environment variable to be set. 

`secrets.yml`

```yaml
- name: secretX
  type: credential
  username: xxx
  password: xxx
- name: secretY
  type: token
  token: yyy
- name: servicenow
  type: hashicorp-vault
  uri: https://vault.example.com/v1/test/data/servicenow
```

Future ideas:
- Use a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.) to store the secrets
- Use a database to store the secrets
- CyberArk

**API_TOKEN**   

The service has a rest api wrapped around the service.   the **API_TOKEN** environment variable will be used to authenticate the requests.  it's a bearer token (Bearer <token>).

TODO : transform the app into a full blown enterprise application with a database for users, roles, ldap, MFA, request tokens, etc.  Redis to store the tokens, etc.  This is a long term goal, for now we will use a simple token.

# entry script

The `main.py` was originally the main entry, but after adding the api, the logic has been moved to the api.py file, because the api.py file will become the main entry point.  The `main.py` is a wrapper around `lib.prow_processor.api.py` for testing.  

For now the api uses app.run, but in the future it will be moved to a wsgi server (gunicorn, uWSGI, etc.) for production use.  This will require the logging to be moved to the app level.  For now I have been testing on my laptop (windows) so gunicorn is not an option.  Looking for some python magicians to help me with this.

# flow_processor
  
The flow_processor is the main module of the application.  It will be used to create the flows and steps.  It will also be used to run the flows and steps.  The flow_processor will be used by the `api.py` file to run the flows.

# the flow class

The flow class is quite simple.  It has a name, an optional schedule property (**cron** or **every_seconds**) and a list of steps.  

The flow instance has a few properties:

- **_data**: a dict that will hold the data during the flow
- **_steps**: a list of steps that will be executed in order

# the step class

The step class is the main class for the steps.  It has some generic properties that will be used by all steps. (**name**, **type**, **when**, ...).
Each step handles data in some form (load, read, transform, write, send).  
We use the `factory.py` to create the steps.  Currently these are the steps that are implemented:

| Step Name             | Description                                                                                  |
|-----------------------|----------------------------------------------------------------------------------------------|
| **FileStep**          | Reads from or writes to a file                                                               |
| **RestStep**          | Calls a REST API (GET, POST, PUT, DELETE, PATCH)                                             |
| **JqStep**            | Uses jq to transform the data                                                                |
| **JinjaStep**         | Uses jinja2 to transform the data                                                            |
| **FlowStep**          | Calls another flow                                                                           |
| **FlowLoopStep**      | Calls another flow in a loop                                                                 |
| **JiraNamesMergeStep**| Reformats fields from Jira results, merging the names/labels                                 |

Some ideas for future steps:
- **SwitchStep**: a step that will switch the data (if/else) or (match/case)
- **DatabaseStep**: a step that will read from or write to a database
- **KafkaStep**: a step that will read from or write to a kafka topic
- **S3Step**: a step that will read from or write to an S3 bucket
- **RedisStep**: a step that will read from or write to a redis database
- **EmailStep**: a step that will send an email

Each step has a **result_key** property that will be used to store the result of the step in the **_data** property.  
Each step also has a custom property (**file**, **rest**, **jq**, ...) which hold the typical properties for that step.  For example, the **FileStep** has a **path** property, the **RestStep** has a **uri** property, etc.  Some of these steps will have a **data_key** property which will be the input payload for that step.  
All steps can have **jq_expression** (json query) property that can do quick final transformation on the data.

Common properties for all steps:

| Property         | Description                                                                                                    |
|------------------|----------------------------------------------------------------------------------------------------------------|
| **name**         | The name of the step                                                                                           |
| **type**         | The type of the step (file, rest, jq, ...)                                                                     |
| **when**         | A condition (if/else) that determines whether the step should be executed                                      |
| **result_key**   | The key used to store the result of the step in the **_data** property                                         |
| **ignore_errors**| A list of regex patterns to match error strings that should be ignored, allowing the flow to continue on error |
| **jq_expression**| A jq expression to transform the data after the step is executed                                               |
## The file step

The file step is a step that will read from or write to a file.

| Property   | Description                                                                                  | Notes                                   | Default |
|------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **path**   | The path to the file                                                                         | Allows jinja2 templating; relative to DATA_PATH |         |
| **mode**   | The mode of the file                                                                         |                                         | read    |
| **type**   | The type of the file                                                                         | (json, yaml)                            |         |
| **data_key** | The key used to grab the data from the **_data** property to write to the file             |                                         |         |

## The rest step

The rest step is a step that will call a REST API (GET, POST, PUT, DELETE, PATCH).

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **uri**     | The URI of the REST API                                                                      | Allows jinja2 templating                |         |
| **method**  | The HTTP method to use                                                                       | (GET, POST, PUT, DELETE, PATCH)         | GET     |
| **headers** | The headers for the REST API (JSON)                                                          |                                         |         |
| **body**    | The body for the REST API (JSON)                                                             |                                         |         |
| **data_key**| The key used to grab the data from the **_data** property to send to the REST API            | Higher in hierarchy than **body**       |         |
| **authentication** | The authentication dict                                |                                         |         |

| Property   | Description                                                                                       | Notes / Default                |
|------------|---------------------------------------------------------------------------------------------------|-------------------------------|
| **type**   | The type of authentication                                                                        | `basic`, `token`, `api-key` (header key-value) |
| **secret** | The secret to use for authentication                                                              | Should return the proper type  |
| **bearer** | The bearer prefix to use for token authentication (e.g., `Bearer <token>`)                        | Default: `Bearer`              |

## The jq step

The jq step is a step that will use jq to transform the data.

| Property      | Description                                                                                  | Notes                                   | Default |
|---------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **expression**| The jq expression to transform the data                                                      |                                         |         |
| **data_key**  | The key used to grab the data from the **_data** property to transform                       |                                         |         |

## The jinja step

The jinja step is a step that will use jinja2 to transform the data.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **path**    | The jinja2 template to use for transformation                                                | Relative to TEMPLATES_PATH              |         |
| **data_key**| The key used to grab the data from the **_data** property to transform                       |                                         |         |
| **parse**   | Optionally parse the data as JSON or YAML                                                    | No parsing, just a string               |         |

## The flow step

The flow step is a step that will call another flow. Useful for reusing flows and creating complex flows.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **path**    | The path of the flow to call                                                                 | Relative to FLOWS_PATH                  |         |
| **data_key**| The key used to grab the data from the **_data** property to send to the flow                |                                         |         |

## The flow loop step

The flow loop step is a step that will call another flow in a loop.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **path**    | The path to the flow to call                                                                 | Relative to FLOWS_PATH                  |         |
| **data_key**| The key used to grab the data from the **_data** property to send to the flow                | Must be a list of items to loop over    |         |

## The jira names merge step

The jira names merge step is a custom step that reformats fields from Jira results, merging the names/labels.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **data_key**| The key used to grab the data from the **_data** property to transform                       |                                         |         |
| **list_key**| The key used to grab the list of items to loop over in the results                           |                                         | issues  |

Note: The `expand=names` query must be used so Jira adds the names to the result.

# The flow scheduler

The flow scheduler is a simple scheduler that will run the flows based on a cron expression or every x seconds.  It will use the `schedule` library to run the flows.  The scheduler will run in a separate thread and will use the `flow_processor` to run the flows.  
  

> **API Documentation**  
>  
> Access the interactive Swagger UI at:  
>  
> ```
> /api/docs
> ```

## Add a flow

You can add a flow by path (relative to FLOWS_PATH).  It's will stored in the scheduler with a guid, so it can later be retrieved or removed.

The schedule will automatically search for the **autostart** property in the config file, which is a list of relative paths.  The scheduler will add the flows to the scheduler and start them.  The autostart property is optional, if not present, the scheduler will not start any flows.

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

The **launch_flow** method will launch a flow.  The flow is launched by path (relative to FLOWS_PATH).  

## Get locks

To make sure that the flows are not running at the same time, we will use locks.  The locks are stored in the **LOCK_PATH** directory.  The locks are created by the `flow_processor` and are removed when the flow is finished.  There is no timeout on the locks.  If the application should be terminated, the locks will be removed at first start.  

Use the api `/api/locks` to get the list of locks.  

## Remove lock

Use the api `/api/locks/{flow_name}` DELETE to remove a lock.  The lock is removed by flow_name.

## Remove all locks
Use the api `/api/locks` DELETE to remove all locks.  The locks are removed by flow_name.
