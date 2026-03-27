from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stib_client import StopConfig, StibClient, _extract_notice_linked_date, _extract_notice_text


class FakeClient(StibClient):
    def __init__(self, waiting_records=None, traveller_records=None):
        super().__init__(source="belgian_mobility")
        self.waiting_records = waiting_records or []
        self.traveller_records = traveller_records or []

    def _request_json(self, path, params=None):
        if path == "/rt/WaitingTimes":
            return {"results": self.waiting_records}
        if path == "/rt/TravellersInformation":
            return {"results": self.traveller_records}
        raise AssertionError(f"Unexpected path {path}")


STOPS = [
    StopConfig(label="toward ALBERT", pointid="5830", destination="ALBERT", static_id="5830F"),
    StopConfig(label="toward VAN HAELEN", pointid="0711", destination="VAN HAELEN", static_id="0711F"),
]
MONITORED_LINES = ["1", "2", "5", "6", "18", "4", "10", "92"]


def test_departures_are_grouped_and_sorted():
    client = FakeClient(
        waiting_records=[
            {
                "pointid": "5830",
                "passingtimes": (
                    '[{"destination":{"fr":"ALBERT"},"expectedArrivalTime":"2099-03-27T10:40:00+01:00"},'
                    '{"destination":{"en":"ALBERT"},"expectedArrivalTime":"2099-03-27T10:31:00+01:00"}]'
                ),
            },
            {
                "pointid": "0711",
                "passingtimes": '[{"destination":{"nl":"VAN HAELEN"},"expectedArrivalTime":"2099-03-27T10:33:00+01:00"}]',
            },
        ]
    )

    departures, error = client.get_departures_for_stops("18", STOPS)

    assert error is None
    assert [item["time_local"] for item in departures["5830"]] == ["10:31", "10:40"]
    assert departures["0711"][0]["destination"] == "VAN HAELEN"


def test_past_departures_are_removed():
    client = FakeClient(
        waiting_records=[
            {
                "pointid": "5830",
                "passingtimes": (
                    '[{"destination":{"fr":"ALBERT"},"expectedArrivalTime":"2001-03-27T10:10:00+01:00"},'
                    '{"destination":{"fr":"ALBERT"},"expectedArrivalTime":"2099-03-27T10:10:00+01:00"}]'
                ),
            }
        ]
    )

    departures, _ = client.get_departures_for_stops("18", STOPS)

    assert len(departures["5830"]) == 1
    assert departures["5830"][0]["time_local"] == "10:10"


def test_traveller_notice_prefers_english_and_marks_relevance():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Line 18 diversion at Albert","fr":"Deviation ligne 18 a Albert"}]}]',
                "lines": '[{"id":"18"}]',
                "points": '[{"id":"0711"}]',
                "priority": 6,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"fr":"Other line notice only"}]}]',
                "lines": '[{"id":"81"}]',
                "points": '[]',
                "priority": 4,
                "type": "LongText",
            },
        ]
    )

    notices, error = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert error is None
    assert notices[0]["text"] == "Line 18 diversion at Albert"
    assert notices[0]["relevance"] == 3
    assert notices[0]["scope_label"] == "For your route"
    assert notices[0]["linked_date"] is None


def test_traveller_notice_falls_back_to_high_priority_monitored_line():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Lower priority unrelated tram notice"}]}]',
                "lines": '[{"id":"54"}]',
                "points": '[]',
                "priority": 4,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"High priority line 4 notice"}]}]',
                "lines": '[{"id":"4"}]',
                "points": '[]',
                "priority": 6,
                "type": "LongText",
            },
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert notices[0]["text"] == "High priority line 4 notice"
    assert notices[0]["scope_label"] == "For your route"


def test_traveller_notice_list_is_capped_at_six():
    client = FakeClient(
        traveller_records=[
            {
                "content": f'[{{"text":[{{"en":"Notice {idx}"}}]}}]',
                "lines": '[{"id":"18"}]',
                "points": "[]",
                "priority": 5,
                "type": "LongText",
            }
            for idx in range(8)
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert len(notices) == 6


def test_traveller_notice_filters_generic_messages_and_cleans_spacing():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"fr":"Bon voyage sur nos lignes."}]}]',
                "lines": "[]",
                "points": "[]",
                "priority": 9,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"Works. Stop moved.Stop now on avenue Brugmann."}]}]',
                "lines": '[{"id":"18"}]',
                "points": "[]",
                "priority": 6,
                "type": "LongText",
            },
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert len(notices) == 1
    assert notices[0]["text"] == "Works. Stop moved. Stop now on avenue Brugmann."


def test_traveller_notice_deduplicates_similar_event_branches():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Emergency drill. 29 Mar until 2pm, M1 limited to ALMA. M-bus between ROODEBEEK and STOKKEL."}]}]',
                "lines": '[{"id":"1"}]',
                "points": '[]',
                "priority": 5,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"Emergency drill. 29 Mar until 2pm, M1 limited to ALMA. M-bus at stop of bus N05 to KRAAINEM."}]}]',
                "lines": '[{"id":"1"}]',
                "points": '[]',
                "priority": 5,
                "type": "LongText",
            },
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert len(notices) == 1


def test_traveller_notice_excludes_unmonitored_and_network_wide_updates():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Network-wide notice"}]}]',
                "lines": '[]',
                "points": '[]',
                "priority": 8,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"Line 54 notice"}]}]',
                "lines": '[{"id":"54"}]',
                "points": '[]',
                "priority": 7,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"Line 10 notice"}]}]',
                "lines": '[{"id":"10"}]',
                "points": '[]',
                "priority": 5,
                "type": "LongText",
            },
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert [notice["text"] for notice in notices] == ["Line 10 notice"]


def test_traveller_notice_excludes_low_priority_advisories():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Line 18 advisory"}]}]',
                "lines": '[{"id":"18"}]',
                "points": '[]',
                "priority": 4,
                "type": "LongText",
            }
        ]
    )

    notices, _ = client.get_traveller_notices(MONITORED_LINES, STOPS)

    assert notices == []


def test_extract_notice_text_joins_unique_sections():
    text = _extract_notice_text(
        '[{"text":[{"en":"First alert"},{"fr":"Premier avis"}]},{"text":[{"en":"Second alert"}]}]'
    )

    assert text == "First alert Second alert"


def test_extract_notice_linked_date_handles_multilingual_prefixes():
    assert _extract_notice_linked_date("Works. From 6 Jan, line diverted.") == "6 Jan"
    assert _extract_notice_linked_date("Travaux. Dès le 6/1, ligne déviée.") == "6/1"
    assert _extract_notice_linked_date("Werken. Vanaf 7/2, halte verplaatst.") == "7/2"
