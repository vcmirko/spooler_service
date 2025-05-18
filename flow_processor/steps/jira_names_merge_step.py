import logging
from ..step import Step
from flow_processor.utils import string_to_key

class JiraNamesMergeStep(Step):
    """Subclass for file operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "jira_names_merge" in step, "Jira names merge configuration is required"
        self._jira_names_merge = step.get("jira_names_merge")
        self._list_key = self._jira_names_merge.get("list_key", "issues")
        assert "data_key" in self._jira_names_merge, "issues key is required"

    def process(self, ignore_when=False):
        """Process the Jira names merge step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return 

        logging.info("%s -> Transpose Jira customfields with names", self._representation)
        data = self._flow._data.get(self._jira_names_merge.get("data_key"))
        issues = data.get(self._list_key, [])
        field_names = data.get("names", None)
        if field_names is None:
            raise Exception(f"Field names not found in {self._list_key} list, add expand=names to the query")
        
        # clone issues to self._data by value, not reference
        self._data = [issue.copy() for issue in issues]


        # for each issue, go into the issue, field the fields, each key that starts with customfield_ 
        # => add the field name to the issue, copy the value to the field name and remove the custom field
        for issue in self._data:
            for key, value in list(issue["fields"].items()):
                # if value is none or empty list, remove the field
                if value is None or (isinstance(value, list) and not value):
                    # remove the field if the value is null
                    del issue["fields"][key]
                elif key.startswith("customfield_"):
                    # from field_names, get the field.name by field.id
                    field_name = field_names.get(key)
                    if field_name is None:
                        continue
                    
                    if field_name:
                        issue["fields"][string_to_key(field_name)] = value
                        del issue["fields"][key]

        return super().process()
