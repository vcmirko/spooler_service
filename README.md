# Spooler Service (Octoflow?)

A flexible job and flow orchestration service for running, scheduling, and tracking flows (workflows) with robust API and database-backed job management.
> **Note:**  
> This service is designed to run as a **single instance only**. For simplicity and ease of deployment, the jobs database uses SQLite via Python and is managed within the app itself. Running multiple instances would risk duplicate job execution, as SQLite does not support distributed locking.  
> 
> If your workload grows to require multiple instances or high concurrency, the SQLAlchemy data layer can be configured to use an external database (e.g., PostgreSQL, MySQL) to support distributed locking and scaling.  
> 
> **If you anticipate needing this, please contact us to discuss your requirements.**


## Directory Structure

```
├── data/
│   ├── config.yml
│   ├── secrets.yml
│   ├── flows/
│   │   ├── flow1.yml 
│   │   ├── flow2.yml
│   ├── logs/
│   │   ├── spooler_service.log
│   ├── templates/
│   │   ├── template1.j2
│   │   ├── template2.j2
│   ├── jobs.sqlite
│   ├── ... other data files (input, output, etc.)
```

## Environment Variables

All are optional and have sensible defaults.

| Variable         | Description                                 | Default                |
| Variable         | Description                                 | Default                |
|------------------|---------------------------------------------|------------------------|
| **LOG_PATH**     | Full path to the directory for log files         | `<DATA_PATH>/logs/`           |
| **LOG_FILE_NAME**| Name of the log file                        | `spooler_service.log`  |
| **LOG_LEVEL**    | Log level for the application               | `INFO`                 |
| **FLOWS_PATH**   | Full path to the directory for flow files        | `<DATA_PATH>/flows/`          |
| **TEMPLATES_PATH**| Full path to the directory for template files   | `<DATA_PATH>/templates/`      |
| **SECRETS_PATH** | Full path to the secrets file                    | `<DATA_PATH>/secrets.yml`     |
| **CONFIG_FILE**  | Full path to the configuration file              | `<DATA_PATH>/config.yml`      |
| **API_PORT**     | Port for the API server                     | `5000`                 |
| **API_TOKEN**    | Token for API authentication                | `default_token`        |
| **HASHICORP_VAULT_TOKEN** | Token for HashiCorp Vault          |                        |
| **FLOW_TIMEOUT_SECONDS** | Default timeout for flows (seconds) | `600`                  |
| **TIMEZONE**     | Timezone for API input/output (e.g. `UTC`, `Europe/Berlin`) | `UTC` |
| **JOBS_DB_PATH** | Full path to the jobs database file (SQLite)     | `<DATA_PATH>/jobs.sqlite`     |


**TIMEZONE** is used for the cron jobs scheduling, all API output (ISO 8601) and for interpreting incoming date/time filters if no timezone is provided.

## Security & Secrets

Secrets can be stored in `secrets.yml` or fetched from HashiCorp Vault (with 1-minute TTL).  
Set `HASHICORP_VAULT_TOKEN` for Vault access.

Example `secrets.yml`:
```yaml
- name: secretX
  type: credential
  username: xxx
  password: xxx
- name: servicenow
  type: hashicorp-vault
  uri: https://vault.example.com/v1/test/data/servicenow
```

## Job Locking & Concurrency

- **No two jobs for the same flow can run at the same time.**.  The idea of this spooler service was originally to process data, transform it, have it executed somewhere, and return the result.  If the same flow would run concurrently, it could lead to data corruption or unexpected results.
- The jobs table in the database is the single source of truth for running jobs.
- If you try to launch a job for a flow that is already running, the API returns `409 Conflict`


## API Overview

All endpoints require `Authorization: Bearer <API_TOKEN>`.

## API Structure

```
/api/
├── jobs/
│   ├── [POST]      /api/jobs                # Launch a new job
│   ├── [GET]       /api/jobs                # List jobs (with filters)
│   ├── [GET]       /api/jobs/{job_id}       # Get job details
│   ├── [DELETE]    /api/jobs                # Delete jobs 
|   ├── [DELETE]    /api/jobs/{job_id}       # Delete a specific job
│
├── schedules/
│   ├── [POST]      /api/schedules           # Create a new schedule
│   ├── [GET]       /api/schedules           # List schedules
│   ├── [DELETE]    /api/schedules/{id}      # Remove a schedule
│
├── logs/
│   ├── [GET]       /api/logs                # List log files
│   ├── [GET]       /api/logs/{filename}     # Download/view a log file
│
├── docs/
│   ├── [GET]       /api/docs/               # Swagger UI
```

### Launch a Job (Ad Hoc Flow Execution)

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "flow1.yml", "data": {"foo": "bar"}, "timeout_seconds": 120}'
```
**Response:**  
- `{"job_id": "..."}` if started  
- `{"error": "A job for this flow is already running."}` if locked

### List Jobs (with Filtering & Pagination)

```bash
curl -X GET "http://localhost:5000/api/jobs?state=finished&limit=10&offset=0&start_time_from=2024-05-23T00:00:00+02:00"
```
- Supports filters: `state`, `status`, `start_time_from`, `start_time_to`, `end_time_from`, `end_time_to`
- Time filters accept ISO 8601 or human-friendly datetimes (timezone optional; defaults to `TIMEZONE`)

### Get Job Details

```bash
curl -X GET http://localhost:5000/api/jobs/<job_id>
```

### Delete Jobs (all, or filtered)

```bash
curl -X DELETE "http://localhost:5000/api/jobs?older_than_days=30&status=finished&state=success"
```
- Deletes jobs whose `end_time` is older than the specified number of days.
- Supports query parameters:
  - `older_than_days` (optional): Only jobs with `end_time` older than this value (in days) will be deleted.
  - `status` (optional): Filter jobs by status. Possible values: `success`, `failed`, `exit`.
  - `state` (optional): Filter jobs by state. Possible values: `running`, `finished`.
- Returns a summary of deleted jobs.

### Delete a Specific Job

```bash
curl -X DELETE http://localhost:5000/api/jobs/<job_id>
```

### Schedule a Flow

Schedule can be either `cron` or `every_seconds`.
You can also specify a `timeout_seconds` for the schedule.

```bash
curl -X POST http://localhost:5000/api/schedules \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "flow1.yml", "cron": "0 * * * *"}'
```

### List Schedules

```bash
curl -X GET http://localhost:5000/api/schedules
```

### Remove a Schedule

```bash
curl -X DELETE http://localhost:5000/api/schedules/<schedule_id>
```

### View Logs
```bash
curl -X GET http://localhost:5000/api/logs
```

## Time Handling

- Cron schedules will respect the configured `TIMEZONE`.
- All times in API responses are ISO 8601 in the configured `TIMEZONE`.
- All time filters accept ISO 8601 or human-friendly datetimes.  
  If no timezone is provided, the configured `TIMEZONE` is assumed.

## Data handling

- The main flow will have a `_data` dictionary that contains all data passed to the flow.  Every step requiring input data can access this data using the `data_key` property and every step that produces output will store its result in the `_data` dictionary under the specified `result_key`.  See more in the **Flow & Step Model** section below.  
  
**Special Variables:** The flow will have some special variables available in all steps:

| Variable           | Description                                                                                      |
|--------------------|--------------------------------------------------------------------------------------------------|
| **__timestamp__**  | A timestamp of the job start in number format (e.g., `20250526120400`)                           |
| **__job_id__**     | The ID of the job                                                                                |
| **__flow_path__**  | The path of the flow being executed                                                              |
| **__input__**      | The input data passed to the flow, to process passed-on data                                     |
| **__loop_index__** | The index of the current item in a loop                                                          |
| **__errors__**     | A list of errors encountered during the flow execution                                           |

## Flow & Step Model

A **flow** is a YAML file with a list of steps that can be executed in order. Each step can perform various actions, such as calling REST APIs, reading/writing files, transforming data, or executing other flows.  They have the following main properties:

| Property         | Description                                                                                                 |
|------------------|-------------------------------------------------------------------------------------------------------------|
| **name**         | The name of the flow.                                                                                       |
| **steps**        | A list of steps to execute, in order.                                                                       |
| **finally_step** | (Optional) A step that always runs at the end of the flow, even if the flow fails.                          |

Example:
```yaml

# Spooler Service Flow Example, read ticket for service now

# get the tickets
name: Process snow tickets                # Name of the flow
finally_step: "write output file"         # Step that always runs at the end, even if flow fails
steps:
  - name: get tickets
    type: rest                            # REST API call step
    result_key: tickets                   # Store result in 'tickets'
    rest:
      uri: https://dev.service-now.com/api/now/table/x_xxxx   # ServiceNow API endpoint
      query:                                                  # Query parameters for the API call
        sysparm_query: request_type=ansible^status=new
        sysparm_fields: sys_id,sys_created_by,payload,sys_created,sys_created_on,job_id
        sysparm_limit: 5
      authentication:
        type: basic
        secret: snow_credential           # Reference to secret in secrets.yml 
    jq_expression: ".result"              # Extract 'result' field from API response

# there is a special exit step that can be used to exit the flow early, the status will be set to `exit`
# if the exit step is triggered, the finally step will NOT be executed.
- name: Exit early if no tickets found
    type: exit                            # Exit step to stop flow early
    result_key: exit_info                 # Store exit message in 'exit_info'
    exit:
      message: "No tickets found, exiting early."
    when: ["tickets | length == 0"]       # Condition to check if there are no tickets

# process the tickets by looping over them (in parallel) and sending them to AWX, the main flow will wait for all subflows to finish
# the multiple results will be stored in the result_key 'flow_loop'
- name: loop tickets
    type: flow_loop                       # Loop over items and call another flow (multithreading)
    result_key: flow_loop                 # Store result of all subflows in 'flow_loop'
    flow_loop:
      path: ticket_to_awx.yml             # Sub-flow to run for each ticket
      data_key: tickets                   # Input data for the loop (from previous step)
    when: ["tickets | length > 0"]        # Only run if there are tickets

# dump the entire flow result to a file, the file will be written in the output folder with a timestamp
# by setting the `data_key` to `.` (dot), the entire flow result will be used as the input for the file step
- name: write output file
    type: file
    file:
      path: "output/result_{{ __timestamp__ }}.yml" # a job timestamp is available as `__timestamp__`
      mode: write
      type: yaml
      data_key: "."   # dot, means the entire flow result
```

## Step Types

| Step Name             | Description                                                                                  |
|-----------------------|----------------------------------------------------------------------------------------------|
| **FileStep**          | Reads/writes files (JSON/YAML)                                                               |
| **RestStep**          | Calls REST APIs                                                                              |
| **JqStep**            | Transforms data with jq                                                                      |
| **JinjaStep**         | Transforms data with jinja2 templates                                                        |
| **FlowStep**          | Calls another flow                                                                           |
| **FlowLoopStep**      | Calls another flow in a loop                                                                 |
| **JiraNamesMergeStep**| Reformats fields from Jira results                                                           |
| **DebugStep**         | Logs data for debugging                                                                      |
| **SleepStep**         | Pauses execution for a specified number of seconds                                           |
| **ExitStep**          | Prematurely exits the flow with a custom message and sets job status to `exit`               |

Common properties for all steps:

| Property         | Description                                                                                                    |
|------------------|----------------------------------------------------------------------------------------------------------------|
| **name**         | The name of the step                                                                                           |
| **type**         | The type of the step (file, rest, jq, ...)                                                                     |
| **when**         | A condition (if/else) that determines whether the step should be executed                                      |
| **result_key**   | The key used to store the result of the step in the **_data** property                                         |
| **ignore_errors**| A list of regex patterns to match error strings that should be ignored, allowing the flow to continue on error |
| **jq_expression**| A jq expression to transform the data after the step is executed

**NOTE:** Each step will have its own specific property, matching the step type (e.g., `rest`, `file`, etc.).  Even if a step has just one property, we still wrap it for a consistent interface.

### Sleep Step

Pauses the flow for a specified number of seconds.  Can be useful for testing or pacing API calls.

```yaml
- name: sleep before processing
  type: sleep
  sleep:
    seconds: 5
```

### Exit Step

Allows a flow to exit early on purpose (e.g., if there is no data to process).  
When triggered, the flow stops immediately, the job status is set to `exit`, and the provided message is stored in the job result (under the specified `result_key`).

```yaml
- name: exit early
  type: exit
  result_key: exit_info
  exit:
    message: "No data to process, exiting early."
  when:
    - "tickets | length == 0"
```

Setting to a different status, makes it easy to distinguish jobs that were exited intentionally (not errors or failures) in your job history and API.

**Note:** The `finally_step` will **not** be executed if the flow exits early using this step.
**Note:** You can schedule a loopback flow to remove exited jobs to keep your job history clean.

### Rest Step

The `rest` step type allows you to call REST APIs.

| Property           | Description                                                                                  | Notes                                   | Default |
|--------------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **uri**            | The URI of the REST API                                                                      | Allows jinja2 templating                |         |
| **method**         | The HTTP method to use                                                                       | (GET, POST, PUT, DELETE, PATCH)         | GET     |
| **headers**        | The headers for the REST API (JSON)                                                          | Must be a dictionary                    |         |
| **body**           | The body for the REST API (JSON)                                                             | Must be a dictionary                    |         |
| **data_key**       | The key used to grab the data from the **_data** property to send to the REST API            | Superseedes **body**, must produce a dictionary |         |
| **authentication** | The authentication dict                                                                      |                                         |         |

The `authentication` property can be used to specify the type of authentication to use for the REST API call.

| Property   | Description                                                                                       | Notes / Default                                 |
|------------|---------------------------------------------------------------------------------------------------|-------------------------------------------------|
| **type**   | The type of authentication                                                                        | `basic`, `token`, `api-key` (header key-value)  |
| **secret** | The secret to use for authentication                                                              | Should return the proper type                   |
| **bearer** | The bearer prefix to use for token authentication (e.g., `Bearer <token>`)                        | Default: `Bearer`                               |

**Note:** The body does NOT support jinja2 templating, but you easily use a jinja step before the REST step to prepare the body data and use `data_key` to pass it to the REST step.  
**Note:** If you use a jinja step to prepare the body of a rest step, use the `parse` property to parse the jinja output as JSON or YAML so it's a valid dictionary for the REST step.

Basic GET:
```yaml
- name: get tickets
  type: rest
  result_key: tickets
  rest:
    uri: https://dev.service-now.com/api/now/table/x_xxxx
    authentication:
      type: basic
      secret: snow_credential
```

GET with query parameters and jq transformation:
```yaml
- name: fetch open tickets
  type: rest
  result_key: tickets
  rest:
    uri: https://dev.service-now.com/api/now/table/ticket
    query:
      status: open
      limit: 10
    authentication:
      type: basic
      secret: snow_credential
  jq_expression: ".result | map(select(.priority == \"high\"))"
```

POST with JSON body:
```yaml
- name: create ticket
  type: rest
  result_key: ticket_response
  rest:
    uri: https://dev.service-now.com/api/now/table/ticket
    method: POST
    headers:
      Content-Type: application/json
    body: 
      title: "New Ticket"
      description: "This is a new ticket created via API."
    authentication:
      type: basic
      secret: snow_credential
```

POST with data_key:
```yaml
- name: create ticket
  type: rest
  result_key: ticket_response
  rest:
    uri: https://dev.service-now.com/api/now/table/ticket
    method: POST
    headers:
      Content-Type: application/json
    data_key: ticket_data  # Use data from the flow => flow._data.ticket_data
    authentication:
      type: basic
      secret: snow_credential
```

### Jinja Step
The `jinja` step type allows you to transform data using Jinja2 templates.

Example:
```yaml
- name: render summary
  type: jinja
  jinja:
    path: summary.j2   # Path to the Jinja2 template file, relative to the templates directory
    data_key: tickets
  result_key: summary
```

### Jq Step
The `jq` step type allows you to transform data using jq.

Example of a jq step that filters tickets with high priority from a list of tickets:
```yaml
- name: filter tickets
  type: jq
  jq:
    expression: ".tickets[] | select(.priority == \"high\")"
  result_key: high_priority_tickets
```

### Flow Step
The `flow` step type allows you to call another flow.  
This flow will NOT be run as an asynchronous job, but as a subflow of the current flow, synchronously.

Example:
```yaml
- name: process ticket
  type: flow
  result_key: ticket_result
  flow:
    path: process_ticket.yml
    data_key: ticket
```

### Flow Loop Step
The `flow_loop` step type allows you to call another flow in a loop.  
These subflows will run in parallel, but synchronously, meaning the main flow will wait for all subflows to finish before continuing.  
No jobs are created for the subflows, they are executed as part of the main flow.

Example of a flow loop step that processes a list of tickets:
```yaml
- name: process tickets
  type: flow_loop
  result_key: ticket_results
  flow_loop:
    path: process_ticket.yml
    data_key: tickets_list    # data_key must procude a list of items to loop over, validated by the step

```
### Jira Names Merge Step
The `jira_names_merge` step type reformats fields from Jira results.  
This is a custom usecase created step.  Jira issues return data in a format `customfield_12345`, which is not very useful for further processing.  However, when querying Jira, you can use the `expand=names` query parameter to get the names of the custom fields.
The `jira_names_merge` step type allows you to transform the Jira results into a more usable format by merging the custom field names with the data.  
The step also removes all the properties that are empty, keep the results clean.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **data_key**| The key used to grab the data from the **_data** property to transform                       |                                         |         |
| **list_key**| The key used to grab the list of items to loop over in the results                           |                                         | issues  |

**Note:** The `expand=names` query parameter must be used so Jira adds the names to the result. (validated by the step)  
  
Example:
```yaml
- name: merge custom fields
  type: jira_names_merge
  result_key: tickets
  jira_names_merge:
    data_key: tickets_raw
    list_key: issues
  jq_expression: "[.[] | {id:.id, key:.key, self:.self}]"
```

### Debug Step
The `debug` step type allows you to log data for debugging purposes.  
  
Example:
```yaml
- name: debug ticket data
  type: debug
  debug:
    data_key: ticket_data
```
### File Step
The `file` step type allows you to read/write files.

| Property   | Description                                                                                  | Notes                                   | Default |
|------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **path**   | The path to the file                                                                         | Allows jinja2 templating; relative to DATA_PATH |         |
| **mode**   | The mode of the file                                                                         |                                         | read    |
| **type**   | The type of the file                                                                         | (json, yaml)                            |         |
| **data_key** | The key used to grab the data from the **_data** property to write to the file             |                                         |         |
  

Example of a file step that reads a JSON file and re-writes the result to a YAML file:
```yaml
- name: read input file
  type: file
  result_key: file_content
  file:
    path: input/data.json
    mode: read
    type: json

- name: write output file
  type: file
  file:
    path: output/result_{{ __timestamp__ }}.yml
    mode: write
    type: yaml
    data_key: "file_content"
```

In the example above, you see the use of `__timestamp__`, which is a special variable available in all steps.

## Scheduler

- Flows can be scheduled via cron or interval (`every_seconds`).
- The scheduler uses the same job system as ad hoc jobs.
- Each scheduled flow tracks its last job ID.



## Advanced Features & Ideas

- Secrets from other managers or database
- Future: User/role management, LDAP, MFA, Redis for tokens
- Extendable with new step types (database, Kafka, S3, etc.)



## API Documentation

Interactive Swagger UI:  
```
/api/docs/
```



**Questions or contributions welcome!**
