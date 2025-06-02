import concurrent.futures
import logging
import threading
import time

from flow_processor.flow import Flow
from flow_processor.job_store import JobState, JobStatus, create_job, update_job


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
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        Flow(
                            path=flow_path, payload=payload or {}, job_id=job_id
                        ).process
                    )
                    result, status_result = future.result(timeout=timeout)
                    status_type = status_result.get("type", "success")
                    status_message = status_result.get(
                        "message", "Flow completed successfully."
                    )
                    match status_type:
                        case "exit":
                            update_job(
                                job_id,
                                state=JobState.finished,
                                status=JobStatus.exit,
                                result=result,
                                end_time=time.time(),
                                errors=status_message,
                            )
                        case "failed":
                            update_job(
                                job_id,
                                state=JobState.finished,
                                status=JobStatus.failed,
                                result=result,
                                end_time=time.time(),
                                errors=status_message,
                            )
                        case "success":
                            update_job(
                                job_id,
                                state=JobState.finished,
                                status=JobStatus.success,
                                result=result,
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
            except concurrent.futures.TimeoutError:
                msg = f"Flow {flow_path} timed out after {timeout} seconds"
                logging.error(msg)
                update_job(
                    job_id,
                    state=JobState.finished,
                    status=JobStatus.failed,
                    errors=msg,
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

        threading.Thread(target=run, daemon=True).start()
        return job_id
