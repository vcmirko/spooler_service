from steps import (
    DebugStep,
    ExitStep,
    FileStep,
    FlowLoopStep,
    FlowStep,
    JinjaStep,
    JiraNamesMergeStep,
    JqStep,
    RestStep,
    SleepStep,
)


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
