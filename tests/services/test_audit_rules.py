from name_processor.services.audit_rules.gender_mismatch import ErrGenderMismatch
from name_processor.models.audit import RuleContext
from name_processor.models.person import Gender


def test_gender_mismatch_rule():
    rule = ErrGenderMismatch()
    ctx = RuleContext(
        person_handle="h1",
        gramps_id="I0001",
        display_name="Test",
        gender=Gender.MALE,
        current_patronymic="Ивановна",  # Incorrect suffix
        father_given_name="Иван",
        reference_year=2000,
        locale="ru",
    )

    change = rule.evaluate(ctx, use_pre_reform=False)
    assert change is not None
    assert "Иванович" in change.suggested_string
