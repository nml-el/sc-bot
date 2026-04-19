from sc_bot.cd_antigens import CD_ANTIGEN_MAP


def test_cd_antigen_map_has_entries() -> None:
    assert len(CD_ANTIGEN_MAP) > 100


def test_cd_antigen_map_keys_are_uppercase() -> None:
    assert all(key == key.upper() for key in CD_ANTIGEN_MAP)


def test_cd_antigen_map_values_are_uppercase() -> None:
    assert all(value == value.upper() for value in CD_ANTIGEN_MAP.values())


def test_known_cd_mappings() -> None:
    assert CD_ANTIGEN_MAP["CD25"] == "IL2RA"
    assert CD_ANTIGEN_MAP["CD20"] == "MS4A1"
    assert CD_ANTIGEN_MAP["CD152"] == "CTLA4"
    assert CD_ANTIGEN_MAP["CD279"] == "PDCD1"
    assert CD_ANTIGEN_MAP["CD326"] == "EPCAM"
