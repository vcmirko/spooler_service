import threading
import concurrent.futures
import time
import logging
from flow_processor.flow import Flow
from flow_processor.job_store import create_job, update_job, JobState, JobStatus

class FlowRunner:


    @staticmethod
    def launch_async(flow_path, payload=None, timeout=None, meta=None):
        job_id = create_job(meta=meta or {"flow_path": flow_path, "payload": payload, "timeout": timeout})
        def run():
            update_job(job_id, state=JobState.running, status=JobStatus.unknown, start_time=time.time())
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(Flow(path=flow_path, payload=payload or {}).process)
                    result = future.result(timeout=timeout)
                    # if an exit step raise FlowExitException, it will have been caught in the flow process and returns a tuple (data + exit)
                    if isinstance(result, tuple) and isinstance(result[1], dict) and result[1].get("exit"):
                        update_job(
                            job_id,
                            state=JobState.finished,
                            status=JobStatus.exit,
                            result=result[0] | result[1].get("exit_result", {}),
                            end_time=time.time(),
                            errors=result[1].get("exit_message")
                        )
                    else:
                        update_job(job_id, state=JobState.finished, status=JobStatus.success, result=result, end_time=time.time())
            except concurrent.futures.TimeoutError:
                msg = f"Flow {flow_path} timed out after {timeout} seconds"
                logging.error(msg)
                update_job(job_id, state=JobState.finished, status=JobStatus.failed, errors=msg, end_time=time.time())
            except Exception as e:
                logging.error(f"Flow {flow_path} failed: {e}")
                update_job(job_id, state=JobState.finished, status=JobStatus.failed, errors=str(e), end_time=time.time())
        threading.Thread(target=run, daemon=True).start()
        return job_id