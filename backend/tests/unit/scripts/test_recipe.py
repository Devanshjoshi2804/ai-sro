from scripts.recipe import as_yaml


def test_the_view_prints_as_yaml_for_reading() -> None:
    assert as_yaml({"a": [{"b": 1}], "c": []}) == ["a:", "  - b: 1", "c: []"]
    assert as_yaml({"steps": [{"order": 0, "lanes": ["api", "ui"]}]}) == [
        "steps:",
        "  - order: 0",
        "    lanes:",
        '      - "api"',
        '      - "ui"',
    ]
