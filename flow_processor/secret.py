class Secret:
    """
    Base class for handling secrets.
    """

    def __init__(self, secret_def):
        self._name = secret_def.get("name")
