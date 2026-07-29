"""
Pure-logic unit tests for match_schema.py

These tests mock out the real Hugging Face network calls
(get_dataset_config_names, load_dataset_builder) so they run fast,
offline, and only test the matching logic -- not HF's API or network.
"""

from unittest.mock import patch, MagicMock
import pytest

from match_schema import build_lookup, check_config_names, check_feature_schema, match_schema


# -- fake language data, shaped like the real list_of_languages.json
FAKE_LANGUAGE_DATA = {
    "tier_one": {
        "bam": {"english_names": ["bambara"], "native_names": ["Bamanankan"]}
    },
    "tier_two": {
        "ltz": {"english_names": ["Luxembourgish"], "native_names": ["Lëtzebuergesch"]}
    },
    "tier_three": {
        "eng": {"english_names": ["english"], "native_names": []}
    },
}


# ------Build Lookup------

def test_build_lookup_includes_iso_codes():
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    assert "bam" in lookup
    assert lookup["bam"] == ("bam", "tier_one")



def test_build_lookup_includes_english_names_normalized():
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    assert "luxembourgish" in lookup
    assert lookup["luxembourgish"] == ("ltz", "tier_two")



def test_build_lookup_includes_accents_stripped():
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    # Lëtzebeurgesch should be findable even without the accent
    assert "letzebuergesch" in lookup



def test_build_lookup_no_native_names():
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    # 'eng' has no native names - should not crash, should still have english in the dictionary
    assert "english" in lookup



#----------------Check config names----------------
@patch("match_schema.get_dataset_config_names")
def check_config_names_matches_iso_code_config(mock_get_configs):
    mock_get_configs.return_value = ["bam", "ltz", "unrelated_config"]
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches = check_config_names("fake/repo", lookup)

    assert "bam" in matches
    assert "ltz" in matches
    assert "unrelated_config" not in [m for m in matches]
    assert "bam:config" in matches["bam"]["matched_via"]



@patch("match_schema.get_dataset_config_names")
def test_check_config_names_no_matches(mock_get_configs):
    mock_get_configs.return_value = ["totally_unrelated", "another_one"]
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches = check_config_names("fake/repo", lookup)

    assert matches == {}



@patch("match_schema.get_dataset_config_names")
def test_check_config_handles_exceptions_gracefully(mock_get_configs):
    mock_get_configs.side_effect = Exception("network error")
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches = check_config_names("fake/repo", lookup)

    assert matches == {} # error should not raise, should still return an empty dictionary



#----------------Check feature schema----------------
@patch("match_schema.load_dataset_builder")
def test_check_feature_schema_detects_lang_hint_column(mock_load_builder):
    mock_builder = MagicMock()
    mock_builder.info.features = {"text": "Value(dtype='string'", "language": "Value(dtype='string'"}
    mock_load_builder.return_value = mock_builder
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches, lang_columns = check_feature_schema("fake/repo", lookup)

    assert "language" in lang_columns



@patch("match_schema.load_dataset_builder")
def test_feature_schema_detects_translation_dict_keys(mock_load_builder):
    mock_builder = MagicMock()
    # simulate how a Translation feature prints, e.g. Translation(languages=['bam', 'ltz'])
    fake_feature = MagicMock()
    fake_feature.__str__.return_value = "Translation(languages=['bam', 'ltz'])"
    mock_builder.info.features = {"translation": fake_feature}
    mock_load_builder.return_value = mock_builder
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches,lang_columns = check_feature_schema("fake/repo", lookup)

    assert "bam" in matches
    assert "ltz" in matches
    assert "feature_key:bam" in matches["bam"]["matched_via"]



@patch("match_schema.load_dataset_builder")
def test_feature_schema_handles_exception_gracefully(mock_load_builder):
    mock_load_builder.side_effect = Exception("network error")
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches, lang_data = check_feature_schema("fake/repo", lookup)

    assert matches == {}
    assert lang_data == []



@patch("match_schema.load_dataset_builder")
def test_feature_schema_handles_none_features(mock_load_builder):
    mock_builder = MagicMock()
    mock_builder.info.features = None
    mock_load_builder.return_value = mock_builder
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches, lang_columns = check_feature_schema("fake/repo", lookup)

    assert matches == {}
    assert lang_columns == []



#----------------KNOWN GAP: script/region-suffixed config names----------------
# FLORES-200 style datasets use configs like "eng_Latn", "bam_Latn" (language + script_code).
# Our lookup only has bare 3-character iso codes like "eng", "bam", etc. -- these will currently NOT match.
    # Potential fixes: add a check in `lookup` that finds an `_` and splits and takes [0] as the iso code
# This test documents that gap rather than hiding it, so it doesn't get "fixed" silently
# by a future refactor without anyone noticing the behavior changed.

@patch("match_schema.get_dataset_config_names")
def test_config_names_does_not_match_script_suffixed_codes_yet(mock_get_configs):
    mock_get_configs.return_value = ["eng_Latn", "bam_Latn"]
    lookup = build_lookup(FAKE_LANGUAGE_DATA)
    matches = check_config_names("fake/repo", lookup)

    # AS STATED ABOVE, THIS TEST IS EXPECT TO FAIL. It is documenting CURRENT behavior, not desired outcome
    assert matches == {}



#----------------match_schema (orchestration)----------------
@patch("match_schema.load_dataset_builder")
@patch("match_schema.get_dataset_config_names")
def test_match_schema_merges_config_and_feature_matches(mock_get_configs, mock_load_builder):
    mock_get_configs.return_value = ["bam"]
    mock_builder = MagicMock()
    mock_load_builder.info.features = {"text": "Value(dtype='string')"}
    mock_load_builder.return_value = mock_builder
    matches, needs_content_check = match_schema("fake/repo", FAKE_LANGUAGE_DATA)

    assert "bam" in matches
    assert "config:bam" in matches["bam"]["matched_via"]
    assert  needs_content_check == []



if __name__ == "__main__":
    pytest.main([__file__, "v"])