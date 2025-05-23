# Spooler Service (Octoflow?)

A flexible job and flow orchestration service for running, scheduling, and tracking flows (workflows) with robust API and database-backed job management.
> **Note:**  
> This service is designed to run as a **single instance only**. For simplicity and ease of deployment, the jobs database uses SQLite via Python and is managed within the app itself. Running multiple instances would risk duplicate job execution, as SQLite does not support distributed locking.  
> 
> If your workload grows to require multiple instances or high concurrency, the SQLAlchemy data layer can be configured to use an external database (e.g., PostgreSQL, MySQL) to support distributed locking and scaling.  
> 
> **If you anticipate needing this, please contact us to discuss your requirements.**
---

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

---

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


**TIMEZONE** is used for all API output (ISO 8601) and for interpreting incoming date/time filters if no timezone is provided.

---

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

---

## Job Locking & Concurrency

- **No two jobs for the same flow can run at the same time.**
- The jobs table in the database is the single source of truth for running jobs.
- If you try to launch a job for a flow that is already running, the API returns `409 Conflict`.

---

## API Overview

All endpoints require `Authorization: Bearer <API_TOKEN>`.

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

### Delete Jobs Older Than X Days

```bash
curl -X DELETE "http://localhost:5000/api/jobs?older_than_days=30"
```
- Deletes jobs whose `end_time` is older than X days.

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

---

## Time Handling

- **All times in API responses are ISO 8601 in the configured `TIMEZONE`.**
- **All time filters accept ISO 8601 or human-friendly datetimes.**  
  If no timezone is provided, the configured `TIMEZONE` is assumed.

---

## Flow & Step Model

A **flow** is a YAML file with a `name` and a list of steps. Scheduling information (such as `cron` or `every_seconds`) as well as `timeout_seconds` is **not** part of the flow file itself; it is provided separately when launching a job or creating a schedule.

Flows can also define a `finally_step`, which is a step that always runs at the end of the flow, even if the flow fails.

Example:
```yaml
name: Process snow tickets                # Name of the flow
finally_step: "write output file"         # Step that always runs at the end, even if flow fails
steps:
  - name: get tickets
    type: rest                            # REST API call step
    result_key: tickets                   # Store result in 'tickets'
    rest:
      uri: https://dev.service-now.com/api/now/table/x_xxxx   # ServiceNow API endpoint
      authentication:
        type: basic
        secret: snow_credential           # Reference to secret in secrets.yml 
    jq_expression: ".result"              # Extract 'result' field from API response
  - name: loop tickets
    type: flow_loop                       # Loop over items and call another flow (multithreading)
    result_key: flow_loop                 # Store result of all subflows in 'flow_loop'
    flow_loop:
      path: ticket_to_awx.yml             # Sub-flow to run for each ticket
      data_key: tickets                   # Input data for the loop (from previous step)
    when: ["tickets | length > 0"]        # Only run if there are tickets
  - name: read input file
    type: file
    file:
      path: input/data.json
      mode: read
      type: json
    result_key: file_content

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

---

Common properties for all steps:

| Property         | Description                                                                                                    |
|------------------|----------------------------------------------------------------------------------------------------------------|
| **name**         | The name of the step                                                                                           |
| **type**         | The type of the step (file, rest, jq, ...)                                                                     |
| **when**         | A condition (if/else) that determines whether the step should be executed                                      |
| **result_key**   | The key used to store the result of the step in the **_data** property                                         |
| **ignore_errors**| A list of regex patterns to match error strings that should be ignored, allowing the flow to continue on error |
| **jq_expression**| A jq expression to transform the data after the step is executed

### Sleep Step

Pauses the flow for a specified number of seconds.

```yaml
- name: sleep before processing
  type: sleep
  sleep:
    seconds: 5
```

---

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

This makes it easy to distinguish jobs that were exited intentionally (not errors or failures) in your job history and API.

---

### Rest Step

The `rest` step type allows you to call REST APIs.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **uri**     | The URI of the REST API                                                                      | Allows jinja2 templating                |         |
| **method**  | The HTTP method to use                                                                       | (GET, POST, PUT, DELETE, PATCH)         | GET     |
| **headers** | The headers for the REST API (JSON)                                                          |                                         |         |
| **body**    | The body for the REST API (JSON)                                                             |                                         |         |
| **data_key**| The key used to grab the data from the **_data** property to send to the REST API            | Higher in hierarchy than **body**       |         |
| **authentication** | The authentication dict                                |                                         |         |

The `authentication` property can be used to specify the type of authentication to use for the REST API call.

| Property   | Description                                                                                       | Notes / Default                |
|------------|---------------------------------------------------------------------------------------------------|-------------------------------|
| **type**   | The type of authentication                                                                        | `basic`, `token`, `api-key` (header key-value) |
| **secret** | The secret to use for authentication                                                              | Should return the proper type  |
| **bearer** | The bearer prefix to use for token authentication (e.g., `Bearer <token>`)                        | Default: `Bearer`              |


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
    body: |
      {
        "short_description": "{{ issue_summary }}",
        "description": "{{ issue_details }}"
      }
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
    data_key: ticket_data  # Use data from the flow
    authentication:
      type: basic
      secret: snow_credential
```

### Jinja Step
The `jinja` step type allows you to transform data using Jinja2 templates.

```yaml
- name: render summary
  type: jinja
  jinja:
    path: templates/summary.j2
    data_key: tickets
  result_key: summary
```

### Jq Step
The `jq` step type allows you to transform data using jq.

```yaml
- name: filter tickets
  type: jq
  jq:
    expression: ".tickets[] | select(.priority == \"high\")"
  result_key: high_priority_tickets
```

### Flow Step
The `flow` step type allows you to call another flow.

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

```yaml
- name: process tickets
  type: flow_loop
  result_key: ticket_results
  flow_loop:
    path: process_ticket.yml
    data_key: tickets_list

```
### Jira Names Merge Step
The `jira_names_merge` step type reformats fields from Jira results.

| Property    | Description                                                                                  | Notes                                   | Default |
|-------------|----------------------------------------------------------------------------------------------|-----------------------------------------|---------|
| **data_key**| The key used to grab the data from the **_data** property to transform                       |                                         |         |
| **list_key**| The key used to grab the list of items to loop over in the results                           |                                         | issues  |

Note: The `expand=names` query must be used so Jira adds the names to the result.


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

Example of a file step that reads a JSON file and writes the result to a YAML file:
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



## Scheduler

- Flows can be scheduled via cron or interval (`every_seconds`).
- The scheduler uses the same job system as ad hoc jobs.
- Each scheduled flow tracks its last job ID.

---

## Advanced Features & Ideas

- Secrets from other managers or database
- Future: User/role management, LDAP, MFA, Redis for tokens
- Extendable with new step types (database, Kafka, S3, etc.)

---

## API Documentation

Interactive Swagger UI:  
```
/api/docs/
```

---

**Questions or contributions welcome!**
