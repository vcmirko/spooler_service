import os
import jinja2
import jq
import logging
from datetime import datetime
from dateutil import parser as date_parser
from flow_processor.config import TZ, TEMPLATES_PATH


def apply_jinja2(template, data):
    """Apply Jinja2 templating to the data."""
    try:
        result = jinja2.Template(template).render(data)
        return result
    except jinja2.exceptions.TemplateError as e:
        raise Exception(f"Error processing template: {e}")
    
def apply_jq_filter(data, filter):
    """Apply jq filter to the data."""
    try:
        logging.debug("Applying jq filter: %s", filter)
        logging.debug("Input: %s", data)
        result = jq.compile(filter).input(data).all()
        result = result[0] if len(result) == 1 else None
        logging.debug("Result: %s", result)
        return result
    except Exception as e:
        raise Exception(f"Error applying jq filter: {e}")
    
def apply_jinja2_from_file(path, data):
    """Apply Jinja2 templating from a file."""
    logging.debug("Applying jinja2 from file: %s", path)
    logging.debug("Input: %s", data)
    try:
        with open(os.path.join(TEMPLATES_PATH, path), "r") as file:
            template = file.read()
        result = jinja2.Template(template).render(data)
        logging.debug("Result: %s", result)
        return result
    except jinja2.exceptions.TemplateError as e:
        raise Exception(f"Error processing template: {e}")
    except FileNotFoundError as e:
        raise Exception(f"File not found: {e}")
    
def string_to_key(str):
    """Convert a string to a key."""
    new_key = str.replace(".", "_").replace("-", "_").replace(" ", "_").lower()
    return new_key

def make_timestamp():
    """Generate a unique timestamp."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S")

def to_iso(dt):
    if not dt:
        return None
    return datetime.fromtimestamp(dt, TZ).isoformat()

def parse_time_param(param):
    if not param:
        return None
    try:
        # Try parsing as float (unix timestamp)
        return float(param)
    except ValueError:
        # Parse as date string
        dt = date_parser.parse(param)
        if dt.tzinfo is None:
            # No timezone info: localize to configured TZ
            dt = TZ.localize(dt)
        # Convert to UTC timestamp for DB filtering
        return dt.timestamp()