import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

LOGGER = logging.getLogger(__name__)
BRUSSELS = ZoneInfo("Europe/Brussels")


@dataclass(frozen=True)
class StopConfig:
    label: str
    pointid: str
    destination: str
    static_id: str = ""


class StibClient:
    def __init__(
        self,
        source: str | None = None,
        base_url: str | None = None,
        subscription_key: str | None = None,
        legacy_api_key: str | None = None,
        session: requests.Session | None = None,
        timeout: int = 10,
    ) -> None:
        self.source = (source or os.getenv("STIB_DATA_SOURCE") or "belgian_mobility").strip()
        self.base_url = (
            (base_url or os.getenv("BELGIAN_MOBILITY_BASE_URL") or "")
            .strip()
            .rstrip("/")
            or "https://api-management-discovery-production.azure-api.net/api/datasets/stibmivb"
        )
        self.subscription_key = (
            subscription_key
            if subscription_key is not None
            else os.getenv("BELGIAN_MOBILITY_SUBSCRIPTION_KEY", "").strip()
        )
        self.legacy_api_key = (
            legacy_api_key if legacy_api_key is not None else os.getenv("STIB_API_KEY", "").strip()
        )
        self.timeout = timeout
        self.session = session or requests.Session()

    def get_departures_for_stops(
        self, line_id: str, stops: list[StopConfig]
    ) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
        empty = {stop.pointid: [] for stop in stops}

        try:
            if self.source == "legacy":
                return self._get_legacy_departures_for_stops(line_id, stops), None

            records = self._request_json(
                "/rt/WaitingTimes",
                params={
                    "select": "pointid,lineid,passingtimes",
                    "where": f'lineid="{line_id}"',
                    "limit": 100,
                },
            ).get("results", [])

            return self._normalize_departure_records(records, stops), None
        except Exception as exc:
            LOGGER.exception("Unable to load departures from %s", self.source)
            return empty, "Departures are temporarily unavailable."

    def get_traveller_notices(
        self, line_id: str, stops: list[StopConfig]
    ) -> tuple[list[dict[str, Any]], str | None]:
        try:
            records = self._request_json(
                "/rt/TravellersInformation",
                params={"limit": 254},
            ).get("results", [])
            return self._normalize_traveller_notices(records, line_id, stops), None
        except Exception:
            LOGGER.exception("Unable to load traveller notices")
            return [], "Traveller notices are temporarily unavailable."

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self.subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.subscription_key

        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _get_legacy_departures_for_stops(
        self, line_id: str, stops: list[StopConfig]
    ) -> dict[str, list[dict[str, Any]]]:
        departures_by_stop = {stop.pointid: [] for stop in stops}
        legacy_url = (
            "https://stibmivb.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
            "waiting-time-rt-production/records"
        )

        for stop in stops:
            params = {
                "where": f'lineid="{line_id}" AND pointid="{stop.pointid}"',
                "limit": 100,
            }
            if self.legacy_api_key:
                params["apikey"] = self.legacy_api_key

            response = self.session.get(legacy_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            normalized = self._normalize_departure_records(payload.get("results", []), [stop])
            departures_by_stop[stop.pointid] = normalized.get(stop.pointid, [])

        return departures_by_stop

    def _normalize_departure_records(
        self, records: list[dict[str, Any]], stops: list[StopConfig]
    ) -> dict[str, list[dict[str, Any]]]:
        departures_by_stop = {stop.pointid: [] for stop in stops}
        known_pointids = set(departures_by_stop)
        now = datetime.now(BRUSSELS)

        for record in records:
            pointid = str(record.get("pointid", ""))
            if pointid not in known_pointids:
                continue

            passages = _load_embedded_json(record.get("passingtimes"))
            for passage in passages:
                arrival = _parse_iso_datetime(passage.get("expectedArrivalTime"))
                if not arrival:
                    continue

                arrival_local = arrival.astimezone(BRUSSELS)
                minutes = int((arrival_local - now).total_seconds() // 60)
                if minutes < 0:
                    continue

                destination = _pick_localized_text(passage.get("destination") or {})
                departures_by_stop[pointid].append(
                    {
                        "pointid": pointid,
                        "destination": destination or "?",
                        "time_local": arrival_local.strftime("%H:%M"),
                        "minutes_until": minutes,
                    }
                )

        for pointid, departures in departures_by_stop.items():
            departures.sort(key=lambda departure: departure["minutes_until"])

        return departures_by_stop

    def _normalize_traveller_notices(
        self, records: list[dict[str, Any]], line_id: str, stops: list[StopConfig]
    ) -> list[dict[str, Any]]:
        point_ids = {stop.pointid for stop in stops}
        static_ids = {stop.static_id for stop in stops if stop.static_id}
        relevant_notices: list[dict[str, Any]] = []
        fallback_notices: list[dict[str, Any]] = []
        seen_texts: set[str] = set()

        for record in records:
            text = _extract_notice_text(record.get("content"))
            if not text or text in seen_texts:
                continue

            lines = [line.get("id", "") for line in _load_embedded_json(record.get("lines"))]
            points = [point.get("id", "") for point in _load_embedded_json(record.get("points"))]
            priority = int(record.get("priority") or 0)

            line_match = line_id in lines
            point_match = bool(point_ids.intersection(points) or static_ids.intersection(points))
            relevance = 0
            if line_match:
                relevance += 1
            if point_match:
                relevance += 2

            notice = {
                "text": text,
                "priority": priority,
                "priority_label": _priority_label(priority),
                "priority_tone": _priority_tone(priority),
                "lines": [line for line in lines if line],
                "points": [point for point in points if point],
                "type": record.get("type") or "Notice",
                "relevance": relevance,
                "relevance_label": "For your journey" if relevance else "Across STIB",
                "linked_date": _extract_notice_linked_date(text),
            }

            seen_texts.add(text)
            if relevance:
                relevant_notices.append(notice)
            else:
                fallback_notices.append(notice)

        relevant_notices.sort(key=lambda item: (-item["relevance"], -item["priority"], item["text"]))
        fallback_notices.sort(key=lambda item: (-item["priority"], item["text"]))

        selected = relevant_notices if relevant_notices else fallback_notices
        return selected[:6]


def _load_embedded_json(raw_value: Any) -> list[dict[str, Any]]:
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return raw_value
    try:
        loaded = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value or "T" not in raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _pick_localized_text(value: dict[str, str]) -> str:
    for language in ("en", "fr", "nl"):
        localized = value.get(language)
        if localized:
            return localized.strip()
    for localized in value.values():
        if localized:
            return str(localized).strip()
    return ""


def _extract_notice_text(raw_content: Any) -> str:
    chunks: list[str] = []
    for section in _load_embedded_json(raw_content):
        for text_entry in section.get("text", []):
            localized = _pick_localized_text(text_entry)
            if localized and localized not in chunks:
                chunks.append(localized)
                break
    return " ".join(chunks).strip()


def _extract_notice_linked_date(text: str) -> str | None:
    patterns = (
        r"\b(?:from|From)\s+(\d{1,2}\s+[A-Za-z]+|\d{1,2}(?:/\d{1,2})?)\b",
        r"\b(?:d[eè]s(?:\s+le)?|D[eè]s(?:\s+le)?)\s+(\d{1,2}\s+[A-Za-z]+|\d{1,2}(?:/\d{1,2})?)\b",
        r"\b(?:vanaf|Vanaf)\s+(\d{1,2}\s+[A-Za-z]+|\d{1,2}(?:/\d{1,2})?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _priority_label(priority: int) -> str:
    if priority >= 6:
        return "Major"
    if priority >= 5:
        return "Important"
    return "Advisory"


def _priority_tone(priority: int) -> str:
    if priority >= 6:
        return "major"
    if priority >= 5:
        return "important"
    return "advisory"
