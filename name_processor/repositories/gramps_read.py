import itertools
from collections.abc import Generator

from name_processor.repositories.person import GrampsPersonProxy
from name_processor.protocols.patronymic import PatronymicSubject
from name_processor.protocols.chronology import ChronologySubject


class GrampsReadRepository:
    def __init__(self, dbstate):
        self._db = dbstate.db

    def _get_concrete_proxy(self, handle: str) -> GrampsPersonProxy | None:
        """Private method returning the concrete implementation."""
        gramps_person = self._db.get_person_from_handle(handle)
        if not gramps_person:
            return None
        return GrampsPersonProxy(gramps_person, self._db)

    def get_person_proxy(self, handle: str) -> PatronymicSubject | None:
        return self._get_concrete_proxy(handle)

    def get_chronology_subject(self, handle: str) -> ChronologySubject | None:
        return self._get_concrete_proxy(handle)

    def get_database_median_year(self) -> int | None:
        """
        Calculate the median year from all events in the database.

        :returns: The median year, or None if no events with valid years exist.
        """
        years = []
        for handle in self._db.get_event_handles():
            event = self._db.get_event_from_handle(handle)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        years.append(year)

        if years:
            years.sort()
            return years[len(years) // 2]
        return None

    def get_database_median_year_chunked(self, chunk_size: int = 500) -> Generator:
        """
        Generator that yields None while processing to keep the GUI responsive.
        Returns the final median year via StopIteration when finished.
        """
        years = []
        handles = self._db.get_event_handles()
        handle_iter = iter(handles)

        while True:
            chunk = list(itertools.islice(handle_iter, chunk_size))
            if not chunk:
                break

            for handle in chunk:
                event = self._db.get_event_from_handle(handle)
                if event:
                    date_obj = event.get_date_object()
                    if date_obj and not date_obj.is_empty():
                        year = date_obj.get_year()
                        if year and year > 0:
                            years.append(year)

            # Yield control back to the GTK main loop after processing a chunk
            yield None

        if years:
            years.sort()
            return years[len(years) // 2]

        return None
