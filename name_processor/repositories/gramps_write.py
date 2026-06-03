from gramps.gen.db import DbTxn
from gramps.gen.lib import NameOriginType, Surname


def is_patronymic_origin(orig: NameOriginType) -> bool:
    """
    Checks if a surname origin type indicates a patronymic.
    Casts to int for safe comparison following Gramps convention.
    """
    try:
        return int(orig) == NameOriginType.PATRONYMIC
    except (ValueError, TypeError):
        return False


def update_or_add_patronymic(primary_name, new_patronymic_value) -> str:
    """
    Updates an existing patronymic Surname object in the list, or adds a new one.
    Returns the original patronymic value (or empty string).
    """
    surnames = primary_name.get_surname_list()
    orig_pat = ""
    found = False

    for s in surnames:
        if is_patronymic_origin(s.get_origintype()):
            orig_pat = s.get_surname()
            s.set_surname(new_patronymic_value)
            found = True
            break

    if not found:
        surn_obj = Surname()
        surn_obj.set_surname(new_patronymic_value)
        surn_obj.set_origintype(NameOriginType.PATRONYMIC)
        surn_obj.set_primary(False)
        primary_name.add_surname(surn_obj)

    return orig_pat


class GrampsWriteRepository:
    def __init__(self, dbstate):
        self._db = dbstate.db

    def update_given_names(self, names: dict[str, str]):
        """
        Update the given names of multiple persons in the Gramps database.

        Args:
            names: A dictionary mapping person handles to new given names
        """
        with DbTxn("Update Given Names", self._db) as t:
            for handle, name in names.items():
                person = self._db.get_person_from_handle(handle)
                if not person:
                    continue

                primary_name = person.get_primary_name()
                if not primary_name:
                    continue
                primary_name.set_first_name(name)
                self._db.commit_person(person, t)

    def update_patronymic_names(self, patronymics: dict[str, str]):
        """
        Update the patronymic names of multiple persons in the Gramps database.

        Args:
            patronymics: A dictionary mapping person handles to new patronymics
        """
        with DbTxn("Update Patronymic Names", self._db) as t:
            for handle, patronymic in patronymics.items():
                person = self._db.get_person_from_handle(handle)
                if not person:
                    continue
                primary_name = person.get_primary_name()
                if not primary_name:
                    continue
                update_or_add_patronymic(primary_name, patronymic)
                self._db.commit_person(person, t)
