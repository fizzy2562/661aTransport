from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stib_client import StopConfig, StibClient, _extract_notice_text


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

    notices, error = client.get_traveller_notices("18", STOPS)

    assert error is None
    assert notices[0]["text"] == "Line 18 diversion at Albert"
    assert notices[0]["relevance"] == 3
    assert notices[0]["relevance_label"] == "For your journey"


def test_traveller_notice_falls_back_to_high_priority_network_notice():
    client = FakeClient(
        traveller_records=[
            {
                "content": '[{"text":[{"en":"Lower priority network notice"}]}]',
                "lines": '[{"id":"54"}]',
                "points": '[]',
                "priority": 4,
                "type": "LongText",
            },
            {
                "content": '[{"text":[{"en":"High priority network notice"}]}]',
                "lines": '[]',
                "points": '[]',
                "priority": 6,
                "type": "LongText",
            },
        ]
    )

    notices, _ = client.get_traveller_notices("18", STOPS)

    assert notices[0]["text"] == "High priority network notice"
    assert notices[0]["relevance_label"] == "Across STIB"


def test_extract_notice_text_joins_unique_sections():
    text = _extract_notice_text(
        '[{"text":[{"en":"First alert"},{"fr":"Premier avis"}]},{"text":[{"en":"Second alert"}]}]'
    )

    assert text == "First alert Second alert"
