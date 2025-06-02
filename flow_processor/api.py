import json
import logging
import logging.config
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from .config import (
    API_PORT,
    API_TOKEN,
    LOG_PATH,
    SCRIPT_PATH,
    SWAGGER_JSON_PATH,
    SWAGGER_URL,
)
from .exceptions import (
    FlowAlreadyAddedException,
    FlowNotFoundException,
    FlowParsingException,
)
from .flow import Flow
from .flow_runner import FlowRunner
from .job_store import get_job, list_jobs
from .logs import get_logs
from .scheduler_service import SchedulerService
from .utils import parse_time_param, to_iso

# Flask app setup
app = Flask(__name__)
CORS(app)

logger = logging.getLogger(__name__)

# Load logging configuration
with open(f"{SCRIPT_PATH}/logging_config.json", mode="r") as f:
    logging_config = json.load(f)
    # define the log file path
    logging_config["handlers"]["file"]["filename"] = os.path.join(
        LOG_PATH, logging_config["handlers"]["file"]["filename"]
    )
    logging.config.dictConfig(logging_config)

# get the scheduler instance (singleton)
scheduler_instance = SchedulerService.get_instance()


# --- Only for testing: add StreamHandler for console output ---
def run_app():
    logging.info("Starting Flask app with embedded scheduler (test mode)")
    # launch the Flask app for testing
    app.run(port=API_PORT, use_reloader=False)


@app.route("/static/swagger.json", methods=["GET"])
def get_swagger_json():
    """Dynamically load and modify the Swagger JSON."""
    with open(SWAGGER_JSON_PATH, "r") as f:
        swagger_json = json.load(f)

    # Dynamically modify the Swagger JSON
    # Optionally, you can remove or avoid setting "host" and "schemes" to let Swagger UI use the current browser location.
    swagger_json.pop("host", None)
    swagger_json.pop("schemes", None)
    return jsonify(swagger_json)


# Register Swagger UI
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, "/static/swagger.json")
app.register_blueprint(
    swaggerui_blueprint, url_prefix=SWAGGER_URL, config={"validatorUrl": "localhost"}
)


@app.before_request
def validate_token():
    """Validate the API token."""
    # Skip token validation for Swagger UI and static files
    if request.path.startswith("/api/docs") or request.path.startswith("/static"):
        return None

    token = request.headers.get("Authorization")
    if token != f"Bearer {API_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    return None


# Grouped under /api/v1/schedules


@app.route("/api/v1/schedules", methods=["GET"])
def list_schedules():
    """List all added flows."""

    schedules = scheduler_instance.list_flows()
    # Convert flows to an array of objects with 'id' as a property
    return jsonify({"schedules": schedules}), 200


@app.route("/api/v1/schedules/<schedule_id>", methods=["DELETE"])
def remove_schedule(schedule_id):
    """Remove a scheduled flow by ID."""
    try:
        message = scheduler_instance.remove_flow(schedule_id)
        return jsonify({"status": message}), 200
    except FlowNotFoundException as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error("Error removing schedule: %s", e)
        return jsonify({"error": str(e)}), 500


# Add a new schedule
@app.route("/api/v1/schedules", methods=["POST"])
def add_schedule():
    """Add a new scheduled flow."""
    schedule = request.json
    try:
        schedule_id = scheduler_instance.add_flow(schedule)
        schedule_path = schedule.get("path")
        if schedule_id:
            return jsonify(
                {
                    "status": f"Schedule for '{schedule_path}' added successfully",
                    "schedule_id": schedule_id,
                }
            ), 201
        else:
            return jsonify({"error": "Failed to add schedule"}), 500
    except FlowNotFoundException as e:
        return jsonify({"error": str(e)}), 404
    except FlowAlreadyAddedException as e:
        return jsonify({"error": str(e)}), 409
    except FlowParsingException as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error("Error adding schedule: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/jobs", methods=["POST"])
def launch_job():
    """Launch a flow as a job asynchronously and return a job_id."""
    data = request.json
    flow_path = data.get("path")
    payload = data.get("data")
    timeout = data.get("timeout_seconds")
    meta = {
        "flow_path": flow_path,
        "payload": payload,
        "timeout": timeout,
        "source": "api",
    }
    if not flow_path:
        return jsonify({"error": "flow path is required"}), 400

    try:
        Flow.validate_path(flow_path)
        job_id = FlowRunner.launch_async(
            flow_path, payload=payload, timeout=timeout, meta=meta
        )
    except FlowNotFoundException as e:
        return jsonify({"error": str(e)}), 404
    except FlowParsingException as e:
        return jsonify({"error": str(e)}), 400
    except FlowAlreadyAddedException as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logging.error("Error launching job: %s", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"job_id": job_id}), 202


@app.route("/api/v1/jobs", methods=["GET"])
def list_jobs_api():
    """List all jobs (metadata only) with pagination and filtering."""
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        state = request.args.get("state")
        status = request.args.get("status")
        start_time_from = parse_time_param(request.args.get("start_time_from"))
        start_time_to = parse_time_param(request.args.get("start_time_to"))
        end_time_from = parse_time_param(request.args.get("end_time_from"))
        end_time_to = parse_time_param(request.args.get("end_time_to"))
        # Convert time filters to float if provided
        start_time_from = float(start_time_from) if start_time_from else None
        start_time_to = float(start_time_to) if start_time_to else None
        end_time_from = float(end_time_from) if end_time_from else None
        end_time_to = float(end_time_to) if end_time_to else None
    except ValueError:
        return jsonify({"error": "Invalid parameter"}), 400

    jobs = list_jobs(
        limit=limit,
        offset=offset,
        state=state,
        status=status,
        start_time_from=start_time_from,
        start_time_to=start_time_to,
        end_time_from=end_time_from,
        end_time_to=end_time_to,
    )
    jobs_meta = [
        {
            "id": job.id,
            "meta": job.meta,
            "errors": job.errors,
            "state": job.state.value if job.state else None,
            "status": job.status.value if job.status else None,
            "start_time": to_iso(job.start_time),
            "end_time": to_iso(job.end_time) if job.end_time else None,
        }
        for job in jobs
    ]
    return jsonify({"jobs": jobs_meta, "limit": limit, "offset": offset}), 200


@app.route("/api/v1/jobs/<job_id>", methods=["GET"])
def get_job_api(job_id):
    """Get full details for a specific job."""
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(
        {
            "id": job.id,
            "meta": job.meta,
            "state": job.state.value if job.state else None,
            "status": job.status.value if job.status else None,
            "start_time": to_iso(job.start_time),
            "end_time": to_iso(job.end_time) if job.end_time else None,
            "result": job.result,
            "errors": job.errors,
        }
    ), 200


@app.route("/api/v1/jobs", methods=["DELETE"])
def delete_jobs():
    """
    Delete jobs filtered by end_time (older_than_days), status, and state.
    Query params:
      - older_than_days (int, optional)
      - status (string, optional)
      - state (string, optional)
    """
    try:
        days = request.args.get("older_than_days")
        days = int(days) if days is not None else None
        status = request.args.get("status", None)
        state = request.args.get("state", None)
    except ValueError:
        return jsonify({"error": "Invalid parameter"}), 400

    from flow_processor.job_store import delete_jobs_filtered

    deleted_count = delete_jobs_filtered(days, status, state)
    return jsonify(
        {
            "deleted": deleted_count,
            "older_than_days": days,
            "status": status,
            "state": state,
        }
    ), 200


@app.route("/api/v1/jobs/<job_id>", methods=["DELETE"])
def delete_job_by_id(job_id):
    """
    Delete a specific job by its ID.
    """
    from flow_processor.job_store import delete_job_by_id

    deleted = delete_job_by_id(job_id)
    if deleted:
        return jsonify({"deleted": 1, "job_id": job_id}), 200
    else:
        return jsonify({"error": "Job not found"}), 404


@app.route("/api/v1/logs", methods=["GET"])
def fetch_logs():
    """
    Fetch the latest log lines.
    Query param: lines (int) - number of lines to return (default: 100)
    """
    try:
        lines = int(request.args.get("lines", 100))
    except ValueError:
        return jsonify({"error": "Invalid 'lines' parameter"}), 400

    try:
        logs = get_logs(lines)
        return jsonify({"logs": logs}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"error": e}), 404
    except Exception as e:
        logging.error("Error fetching logs: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    run_app()
