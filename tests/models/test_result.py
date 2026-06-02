from name_processor.models.result import PatronymicInferenceStatus, Context, Result


def test_patronymic_inference_status_enum():
    assert PatronymicInferenceStatus.SUCCESS.value == "SUCCESS"
    assert PatronymicInferenceStatus.NO_ACTIVE_PERSON.value == "NO_ACTIVE_PERSON"
    assert PatronymicInferenceStatus.MORPHOLOGY_FAIL.value == "MORPHOLOGY_FAIL"


def test_context_dataclass_defaults():
    ctx = Context()
    assert ctx.gramps_id is None
    assert ctx.display_name is None
    assert ctx.father_name is None
    assert ctx.reference_year is None
    assert ctx.inferred_patronymic is None
    assert ctx.confidence is None
    assert ctx.rule_source is None


def test_context_dataclass_assignment():
    ctx = Context(
        gramps_id="I0001",
        display_name="Ivan Ivanovich",
        father_name="Ivan",
        reference_year=1900,
        inferred_patronymic="Ivanovich",
        confidence=0.95,
        rule_source="morphology_v1",
    )
    assert ctx.gramps_id == "I0001"
    assert ctx.reference_year == 1900


def test_result_dataclass_defaults():
    res = Result()
    assert res.value is None
    assert res.context is None
    assert res.status is None


def test_result_dataclass_assignment():
    ctx = Context(father_name="Petr")
    res = Result(
        value="Petrovich", context=ctx, status=PatronymicInferenceStatus.SUCCESS
    )
    assert res.value == "Petrovich"
    assert res.context.father_name == "Petr"
    assert res.status == PatronymicInferenceStatus.SUCCESS
