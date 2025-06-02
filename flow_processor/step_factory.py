from .steps.debug_step import DebugStep
from .steps.exit_step import ExitStep  # exits the flow with a message
from .steps.file_step import FileStep
from .steps.flow_loop_step import FlowLoopStep
from .steps.flow_step import FlowStep
from .steps.jinja_step import JinjaStep
from .steps.jira_names_merge_step import JiraNamesMergeStep
from .steps.jq_step import JqStep
from .steps.rest_step import RestStep
from .steps.sleep_step import SleepStep


# Factory function
def create_step(step, flow):
    """Factory function to create a step based on its type."""
    step_type = step.get("type")
    match step_type:
        case "file":
            return FileStep(step, flow)
        case "rest":
            return RestStep(step, flow)
        case "jq":
            return JqStep(step, flow)
        case "jinja":
            return JinjaStep(step, flow)
        case "flow_loop":
            return FlowLoopStep(step, flow)
        case "flow":
            return FlowStep(step, flow)
        case "jira_names_merge":
            return JiraNamesMergeStep(step, flow)
        case "debug":
            return DebugStep(step, flow)
        case "sleep":
            return SleepStep(step, flow)
        case "exit":
            return ExitStep(step, flow)
        case _:
            raise Exception(f"Unsupported step type: {step_type}")
