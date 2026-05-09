import math

import numpy as np
import pandas as pd

from src import parser


def test_create_safe_session_configures_retries_and_mounts():
    session = parser.create_safe_session(retries=7, backoff_factor=1.5)
    http_adapter = session.adapters["http://"]
    https_adapter = session.adapters["https://"]

    assert http_adapter.max_retries.total == 7
    assert http_adapter.max_retries.backoff_factor == 1.5
    assert https_adapter.max_retries.total == 7


def test_calculate_distance_returns_inf_for_none_inputs():
    assert parser.calculate_distance(None, 37.6, 55.7, 37.6) == float("inf")


def test_calculate_distance_is_zero_for_same_point():
    distance = parser.calculate_distance(55.75, 37.61, 55.75, 37.61)
    assert distance == 0


def test_calculate_distance_is_symmetric():
    a_to_b = parser.calculate_distance(55.75, 37.61, 55.78, 37.65)
    b_to_a = parser.calculate_distance(55.78, 37.65, 55.75, 37.61)
    assert math.isclose(a_to_b, b_to_a)


def test_calculate_competitors_metrics_counts_and_average():
    df = pd.DataFrame(
        [
            {"latitude": 55.75, "longitude": 37.61, "rating": 4.0},
            {"latitude": 55.751, "longitude": 37.611, "rating": 5.0},
            {"latitude": 55.78, "longitude": 37.65, "rating": np.nan},
            {"latitude": np.nan, "longitude": 37.60, "rating": 3.0},
        ]
    )

    result = parser.calculate_competitors_metrics(df, radius_300=300, radius_1000=1000)

    assert result.loc[0, "cafes_300m"] == 1
    assert result.loc[0, "cafes_1km"] == 1
    assert math.isclose(result.loc[0, "average_competitor_rating"], 5.0)

    assert result.loc[2, "cafes_300m"] == 0
    assert result.loc[2, "cafes_1km"] == 0
    assert pd.isna(result.loc[2, "average_competitor_rating"])

    assert result.loc[3, "cafes_300m"] == 0
    assert result.loc[3, "cafes_1km"] == 0
    assert pd.isna(result.loc[3, "average_competitor_rating"])


def test_calculate_competitors_metrics_ignores_self():
    df = pd.DataFrame([{"latitude": 55.75, "longitude": 37.61, "rating": 4.4}])

    result = parser.calculate_competitors_metrics(df)

    assert result.loc[0, "cafes_300m"] == 0
    assert result.loc[0, "cafes_1km"] == 0
    assert pd.isna(result.loc[0, "average_competitor_rating"])


def test_calculate_competitors_metrics_skips_invalid_competitor_rating():
    df = pd.DataFrame(
        [
            {"latitude": 55.75, "longitude": 37.61, "rating": 4.0},
            {"latitude": 55.751, "longitude": 37.611, "rating": "bad"},
        ]
    )

    result = parser.calculate_competitors_metrics(df, radius_300=300, radius_1000=1000)

    assert result.loc[0, "cafes_300m"] == 1
    assert result.loc[0, "cafes_1km"] == 1
    assert pd.isna(result.loc[0, "average_competitor_rating"])


def test_get_public_transport_stops_uses_api_result(monkeypatch):
    monkeypatch.setattr(
        parser, "safe_mosru_request", lambda *args, **kwargs: [{"id": 1}, {"id": 2}, {"id": 3}]
    )

    result = parser.get_public_transport_stops()

    assert result == 3000


def test_get_public_transport_stops_fallback(monkeypatch):
    monkeypatch.setattr(parser, "safe_mosru_request", lambda *args, **kwargs: None)

    result = parser.get_public_transport_stops()

    assert result == 8500


def test_get_metro_passenger_flow_parses_api_payload(monkeypatch):
    payload = [
        {
            "Cells": {
                "GlobalID": 1,
                "Name": "Station A",
                "Line": "Line 1",
                "PassengerFlow": "12345",
                "Latitude": "55.7001",
                "Longitude": "37.6002",
            }
        },
        {
            "Cells": {
                "GlobalID": 2,
                "Name": "Station B",
                "Line": "Line 2",
                "PassengerFlow": None,
                "Latitude": None,
                "Longitude": None,
            }
        },
    ]
    monkeypatch.setattr(parser, "safe_mosru_request", lambda *args, **kwargs: payload)

    df = parser.get_metro_passenger_flow_from_mosru()

    assert len(df) == 2
    assert list(df["station_name"]) == ["Station A", "Station B"]
    assert df.loc[0, "passenger_flow"] == 12345
    assert df.loc[0, "latitude"] == 55.7001
    assert df.loc[0, "longitude"] == 37.6002
    assert df.loc[1, "passenger_flow"] == 0
    assert pd.isna(df.loc[1, "latitude"])
    assert pd.isna(df.loc[1, "longitude"])


def test_get_metro_passenger_flow_fallback_when_no_data(monkeypatch):
    fallback_df = pd.DataFrame(
        [{"station_name": "Fallback", "passenger_flow": 1, "latitude": 55.7, "longitude": 37.6}]
    )
    monkeypatch.setattr(parser, "safe_mosru_request", lambda *args, **kwargs: None)
    monkeypatch.setattr(parser, "get_metro_data_fallback", lambda: fallback_df)

    df = parser.get_metro_passenger_flow_from_mosru()

    assert df.equals(fallback_df)


def test_get_metro_passenger_flow_skips_rows_without_globalid(monkeypatch):
    payload = [
        {"Cells": {"Name": "No ID", "PassengerFlow": "100"}},
        {
            "Cells": {
                "GlobalID": 10,
                "Name": "With ID",
                "Line": "Line 3",
                "PassengerFlow": "200",
                "Latitude": "55.71",
                "Longitude": "37.62",
            }
        },
    ]
    monkeypatch.setattr(parser, "safe_mosru_request", lambda *args, **kwargs: payload)

    df = parser.get_metro_passenger_flow_from_mosru()

    assert len(df) == 1
    assert df.loc[0, "station_name"] == "With ID"
    assert df.loc[0, "passenger_flow"] == 200


def test_safe_overpass_request_returns_json_on_200(monkeypatch):
    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"elements": [{"id": 1}]}

    class DummySession:
        @staticmethod
        def post(*args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr(parser, "create_safe_session", lambda *args, **kwargs: DummySession())

    result = parser.safe_overpass_request("query")

    assert result == {"elements": [{"id": 1}]}


def test_get_moscow_coffee_shops_parses_and_deduplicates(monkeypatch):
    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 55.750011, "lon": 37.610011, "tags": {"name": "A", "rating": 4.7}},
            {"type": "node", "id": 2, "lat": 55.750012, "lon": 37.610012, "tags": {"name": "A2", "rating": 4.6}},
            {
                "type": "way",
                "id": 3,
                "center": {"lat": 55.76001, "lon": 37.62001},
                "tags": {"name": "B"},
            },
        ]
    }
    monkeypatch.setattr(parser, "safe_overpass_request", lambda *args, **kwargs: payload)
    monkeypatch.setattr(parser.time, "sleep", lambda *args, **kwargs: None)

    df = parser.get_moscow_coffee_shops()

    assert len(df) == 2
    assert set(df["osm_id"]) == {1, 3}
    assert "Unknown" not in set(df["name"])


def test_get_rent_data_returns_non_empty_dict():
    data = parser.get_rent_data()
    assert isinstance(data, dict)
    assert len(data) > 0
    assert all(value > 0 for value in data.values())


def test_main_returns_dataframe_with_expected_columns(monkeypatch):
    source_df = pd.DataFrame(
        [
            {"latitude": 55.75, "longitude": 37.61, "name": "A", "rating": 4.5, "osm_id": 1},
            {"latitude": 55.751, "longitude": 37.611, "name": "B", "rating": np.nan, "osm_id": 2},
        ]
    )
    metro_df = pd.DataFrame([{"latitude": 55.74, "longitude": 37.60, "passenger_flow": 1000}])
    metrics_df = pd.DataFrame(
        [
            {"cafes_300m": 1, "cafes_1km": 1, "average_competitor_rating": 4.2},
            {"cafes_300m": 1, "cafes_1km": 1, "average_competitor_rating": 4.5},
        ]
    )

    monkeypatch.setattr(parser, "get_moscow_coffee_shops", lambda: source_df.copy())
    monkeypatch.setattr(parser, "get_metro_passenger_flow_from_mosru", lambda: metro_df)
    monkeypatch.setattr(parser, "get_public_transport_stops", lambda: 9000)
    monkeypatch.setattr(parser, "calculate_competitors_metrics", lambda *args, **kwargs: metrics_df)
    monkeypatch.setattr(parser, "get_rent_data", lambda: {"Test": 1234})
    monkeypatch.setattr(parser.time, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, *args, **kwargs: None)

    result = parser.main()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "district" in result.columns
    assert "distance_to_metro" in result.columns
    assert "average_competitor_rating" in result.columns
    assert result["district"].eq("Moscow").all()
    assert result["public_transport_stops_count"].eq(90).all()
    assert not result["rating"].isna().any()
