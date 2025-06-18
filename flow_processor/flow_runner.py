import concurrent.futures
import logging
import time

from flow_processor.flow import Flow
from flow_processor.utils import make_json_safe
from flow_processor.job_store import JobState, JobStatus, create_job, update_job
from flow_processor.config import FLOW_MAX_WORKERS
import json

# Shared executor for all jobs (adjust max_workers as needed)
executor = concurrent.futures.ThreadPoolExecutor(max_workers=FLOW_MAX_WORKERS)


class FlowRunner:
    @staticmethod
    def launch_async(flow_path, payload=None, timeout=None, meta=None):
        job_id = create_job(
            meta=meta
            or {"flow_path": flow_path, "payload": payload, "timeout": timeout}
        )

        def run():
            update_job(
                job_id,
                state=JobState.running,
                status=JobStatus.unknown,
                start_time=time.time(),
            )
            try:
                result, status_result = Flow(
                    path=flow_path, payload=payload or {}, job_id=job_id
                ).process()
                status_type = status_result.get("type", "success")
                status_message = status_result.get(
                    "message", "Flow completed successfully."
                )

                try:
                    # Try to serialize the result as-is
                    json.dumps(result)
                    safe_result = result
                except (TypeError, OverflowError):
                    # If it fails, sanitize it
                    safe_result = make_json_safe(result)
                
                match status_type:
                    case "exit":
                        update_job(
                            job_id,
                            state=JobState.finished,
                            status=JobStatus.exit,
                            result=safe_result,
                            end_time=time.time(),
                            errors=status_message,
                        )
                    case "failed":
                        update_job(
                            job_id,
                            state=JobState.finished,
                            status=JobStatus.failed,
                            result=safe_result,
                            end_time=time.time(),
                            errors=status_message,
                        )
                    case "success":
                        update_job(
                            job_id,
                            state=JobState.finished,
                            status=JobStatus.success,
                            result=safe_result,
                            end_time=time.time(),
                        )
                    case _:
                        logging.error("Unknown status type: %s", status_type)
                        update_job(
                            job_id,
                            state=JobState.finished,
                            status=JobStatus.error,
                            errors=f"Unknown status type: {status_type}",
                            end_time=time.time(),
                        )
            except Exception as e:
                logging.error("Flow %s failed in flow_runner: %s", flow_path, str(e))
                update_job(
                    job_id,
                    state=JobState.finished,
                    status=JobStatus.failed,
                    errors=str(e),
                    end_time=time.time(),
                )

        # Submit the job to the shared executor and handle timeout
        future = executor.submit(run)
        try:
            # This will raise concurrent.futures.TimeoutError if the job takes too long
            future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logging.error(f"Flow {flow_path} timed out after {timeout} seconds")
            update_job(
                job_id,
                state=JobState.finished,
                status=JobStatus.failed,
                errors=f"Flow timed out after {timeout} seconds",
                end_time=time.time(),
            )
        return job_id
