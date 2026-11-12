"""Errors that carry a code the routes may send to the client as is."""


class CodedError(Exception):
    """A refusal named by ``code``: the client gets the code, the log the rest."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
