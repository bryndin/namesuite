from typing import Protocol, Optional

from name_processor.models.person import Gender


class PatronymicSubject(Protocol):
    """The Service dictates the shape of the data it needs."""

    @property
    def handle(self) -> str: ...

    @property
    def gender(self) -> Gender: ...

    @property
    def has_patronymic(self) -> bool: ...

    @property
    def father_handle(self) -> Optional[str]: ...

    @property
    def given_name(self) -> Optional[str]: ...
