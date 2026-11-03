import pytest
from ai.parser import _extract_json_text, parse_ai_response
from ai.schemas import AIDiagnosis


def test_extract_json_from_fence():
    s = "Here is result:\n```json\n{\"root_cause\": \"x\", \"osi_layer\": \"Layer 3\", \"confidence\": 0.5, \"severity\": \"LOW\"}\n```"
    js = _extract_json_text(s)
    assert js is not None


def test_parse_valid_string_json():
    s = '{"root_cause":"x","osi_layer":"Layer 3","confidence":0.2,"severity":"LOW"}'
    d = parse_ai_response(s)
    assert isinstance(d, AIDiagnosis)


def test_parse_malformed_json_raises():
    s = 'not json'
    with pytest.raises(Exception):
        parse_ai_response(s)


def test_json_in_markdown_code_block():
    s = "```\n{\"root_cause\":\"x\",\"osi_layer\":\"Layer 3\",\"confidence\":0.3,\"severity\":\"LOW\"}\n```"
    d = parse_ai_response(s)
    assert isinstance(d, AIDiagnosis)
