from backend.bias import mask_resume, build_bias_check_explanation


def test_mask_removes_name():
    text = "John Smith has 5 years experience in Python."
    masked, fields = mask_resume(text)
    assert "John Smith" not in masked
    assert "name" in fields


def test_mask_removes_pronouns():
    text = "He led a team of 10 engineers and she delivered the project."
    masked, fields = mask_resume(text)
    assert " He " not in masked
    assert " she " not in masked
    assert "pronouns" in fields


def test_mask_removes_university():
    text = "B.Tech from IIT Bombay, 2019."
    masked, fields = mask_resume(text)
    assert "IIT" not in masked
    assert "university name" in fields


def test_mask_neutral_resume_unchanged():
    text = "5 years Python experience. Built production ML pipelines. Led team of 8."
    masked, fields = mask_resume(text)
    # No demographic fields — text should be essentially unchanged
    assert "Python" in masked


def test_explanation_pass():
    record = {"is_biased": False, "delta": 0.002, "masked_fields": ["name"]}
    exp = build_bias_check_explanation(record)
    assert "passed" in exp.lower()
    assert "0.20" in exp


def test_explanation_fail():
    record = {"is_biased": True, "delta": 0.012, "masked_fields": ["name", "pronouns"]}
    exp = build_bias_check_explanation(record)
    assert "flag" in exp.lower()
