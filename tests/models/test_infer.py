import unittest

from name_processor.models.infer import (
    PatronymicInferenceStatus,
    ProposedPatronymic,
)


class TestPatronymicInferenceStatus(unittest.TestCase):
    def test_patronymic_inference_status_enum(self):
        self.assertEqual(PatronymicInferenceStatus.SUCCESS.value, "SUCCESS")
        self.assertEqual(
            PatronymicInferenceStatus.NO_ACTIVE_PERSON.value, "NO_ACTIVE_PERSON"
        )
        self.assertEqual(
            PatronymicInferenceStatus.MORPHOLOGY_FAIL.value, "MORPHOLOGY_FAIL"
        )


class TestProposedPatronymicDataclass(unittest.TestCase):
    def test_proposed_patronymic_dataclass_defaults(self):
        res = ProposedPatronymic()
        self.assertIsNone(res.patronymic)
        self.assertIsNone(res.father_name)
        self.assertEqual(res.status, PatronymicInferenceStatus.UNKNOWN_ERROR)

    def test_proposed_patronymic_dataclass_assignment(self):
        res = ProposedPatronymic(
            patronymic="Petrovich",
            father_name="Petr",
            status=PatronymicInferenceStatus.SUCCESS,
        )
        self.assertEqual(res.patronymic, "Petrovich")
        self.assertEqual(res.father_name, "Petr")
        self.assertEqual(res.status, PatronymicInferenceStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()
