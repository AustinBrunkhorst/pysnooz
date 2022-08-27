from pysnooz.advertisement import get_snooz_display_name


def test_display_name():
    assert get_snooz_display_name("Snooz", "00:00:00:00:00:00") == "Snooz 0000"
    assert get_snooz_display_name("snooz", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_snooz_display_name("sNooZ", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_snooz_display_name("Snooz-DEBF", "00:00:00:00:AB:CD") == "Snooz DEBF"
    assert get_snooz_display_name("Snooz CCCC", "00:00:00:00:AB:CD") == "Snooz CCCC"
    assert get_snooz_display_name("Very custom", "00:00:00:00:AB:CD") == "Very custom"
