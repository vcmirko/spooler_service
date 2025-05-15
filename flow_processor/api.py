from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from flow_processor.config import API_PORT, API_TOKEN, API_HOST, LOCK_PATH, API_PROTOCOLS, LOG_PATH, LOG_FORMAT, LOG_FILE_NAME, CONFIG_FILE, SWAGGER_URL, SWAGGER_JSON_PATH, FLOWS_PATH
from flow_processor.locks import is_locked, create_lock, release_lock, release_all_locks, get_all_locks
from flow_processor.flow import Flow
from flow_processor.flow_scheduler import FlowScheduler
from flow_processor.exceptions import FlowAlreadyAddedException
from flask_cors import CORS
from threading import Thread, Event
import os
import json
import logging
import yaml
import time

# Flask app setup
app = Flask(__name__)
CORS(app)

# --- Logging setup: always log to file, only log to console in test mode ---
log_file_path = os.path.join(LOG_PATH, LOG_FILE_NAME)
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
file_handler.setLevel(logging.INFO)

# Attach file handler to root logger and app.logger
logging.getLogger().addHandler(file_handler)
logging.getLogger().setLevel(logging.INFO)
app.logger.propagate = True

# Global scheduler instance and event
scheduler_instance = None
scheduler_ready = Event()

def start_scheduler():
    global scheduler_instance
    logging.info("Starting scheduler service")
    release_all_locks()
    scheduler_instance = FlowScheduler()
    with open(CONFIG_FILE, "r") as file:
        autostart_flows = yaml.safe_load(file).get("autostart", [])
    try:
        for flow in autostart_flows:
            try:
                scheduler_instance.add_flow(flow)
            except Exception as e:
                logging.error(f"Failed to add flow: {e}")
    
    except Exception as e:
        logging.error(f"Failed to add flows: {e}")
    scheduler_instance.start()
    scheduler_ready.set()
    while True:
        time.sleep(1)

def initialize_scheduler():
    if not scheduler_ready.is_set():
        scheduler_thread = Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()
        scheduler_ready.wait()
        logging.info("Scheduler initialized and ready.")

# --- Only for testing: add StreamHandler for console output ---
def run_app():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    stream_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(stream_handler)
    logging.addHandler(stream_handler)
    logging.logger.info("Starting Flask app with embedded scheduler (test mode)")
    initialize_scheduler()
    app.run(port=API_PORT, use_reloader=False)

# --- Always initialize scheduler, even when running under Gunicorn ---
initialize_scheduler()

@app.route("/static/swagger.json", methods=["GET"])
def get_swagger_json():
    """Dynamically load and modify the Swagger JSON."""
    with open(SWAGGER_JSON_PATH, "r") as f:
        swagger_json = json.load(f)

    # Dynamically modify the Swagger JSON
    swagger_json["host"] = f"{API_HOST}:{API_PORT}"  # Set the host dynamically
    swagger_json["schemes"] = API_PROTOCOLS
    return jsonify(swagger_json)

# Register Swagger UI
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, "/static/swagger.json")
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.before_request
def validate_token():
    """Validate the API token."""
    # Skip token validation for Swagger UI and static files
    if request.path.startswith("/api/docs") or request.path.startswith("/static"):
        return

    token = request.headers.get("Authorization")
    if token != f"Bearer {API_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

# Grouped under /api/locks
@app.route("/api/locks", methods=["GET"])
def get_locks():
    """Get a list of all active locks."""
    locks = get_all_locks()
    return jsonify({"locks": locks})

@app.route("/api/locks", methods=["DELETE"])
def release_all_locks_api():
    """Release all locks."""
    release_all_locks()
    return jsonify({"status": "All locks released."}), 200

@app.route("/api/locks/<flow_name>", methods=["DELETE"])
def release_lock_api(flow_name):
    """Release a specific lock."""
    lock_path = os.path.join(LOCK_PATH, f"{flow_name}.lock")
    if os.path.exists(lock_path):
        release_lock(flow_name)
        return jsonify({"status": f"Lock for {flow_name} released."}), 200
    else:
        return jsonify({"error": f"No lock found for {flow_name}."}), 404

# Grouped under /api/flows

@app.route("/api/flows", methods=["GET"])
def list_flows():
    """List all added flows."""
    if not scheduler_instance:
        return jsonify({"error": "Scheduler is not running"}), 500

    flows = scheduler_instance.list_flows()
    # Convert flows to an array of objects with 'id' as a property
    formatted_flows = [{"id": flow_id, **flow_data} for flow_id, flow_data in flows.items()]
    return jsonify({"flows": formatted_flows}), 200


@app.route("/api/flows/<flow_id>", methods=["DELETE"])
def remove_flow(flow_id):
    """Remove a flow from the scheduler by ID."""
    if not scheduler_instance:
        return jsonify({"error": "Scheduler is not running"}), 500

    success = scheduler_instance.remove_flow(flow_id)
    if success:
        return jsonify({"status": f"Flow with ID '{flow_id}' removed successfully"}), 200
    else:
        return jsonify({"error": f"Flow with ID '{flow_id}' not found"}), 404

@app.route("/api/flows/launch", methods=["POST"])
def launch_flow():
    """Launch a flow, ensuring no duplicate runs."""
    data = request.json
    flow_path = data.get("path")
    payload = data.get("data")
    if not flow_path:
        return jsonify({"error": "flow_path is required"}), 400

    flow_name = os.path.basename(flow_path)
    if is_locked(flow_name):
        return jsonify({"error": f"Flow {flow_name} is already running."}), 409

    try:
        create_lock(flow_name)
        Flow(path=flow_path, payload=payload).process()
        return jsonify({"status": f"Flow {flow_name} executed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        release_lock(flow_name)

@app.route("/api/flows/add", methods=["POST"])
def add_flow_to_scheduler():
    """Add a new flow to the scheduler."""
    if not scheduler_instance:
        return jsonify({"error": "Scheduler is not running"}), 500

    data = request.json
    flow_path = data.get("path")
    if not flow_path:
        return jsonify({"error": "flow_path is required"}), 400

    # Resolve the flow path
    resolved_path = os.path.join(FLOWS_PATH, flow_path)
    if not os.path.exists(resolved_path):
        return jsonify({"error": f"Flow file '{flow_path}' does not exist"}), 404

    try:
        flow_id = scheduler_instance.add_flow(resolved_path)
        if flow_id:
            return jsonify({"status": f"Flow '{flow_path}' added successfully", "flow_id": flow_id}), 201
        else:
            return jsonify({"error": "Failed to add flow"}), 500
    except FlowAlreadyAddedException as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logging.error(f"Failed to add flow: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    run_app()