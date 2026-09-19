from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredLLM(Protocol):
    def complete(self, *, system: str, payload: dict, response_model: type[T]) -> T: ...


class ReplayLLM:
    """Deterministic adapter for tests and cached historical model responses."""

    def __init__(self, responses: list[dict]):
        self.responses = iter(responses)

    def complete(self, *, system: str, payload: dict, response_model: type[T]) -> T:
        del system, payload
        return response_model.model_validate(next(self.responses))
