from src.schemas import IdeaParseResponseData


def test_idea_parser_schema_maps_aliases_to_backend_dictionary():
    payload = {
        "category": "Кофейня",
        "audience": ["офисные сотрудники"],
        "location": ["рядом с метро Лубянка"],
        "request_type": "location_search",
        "problem": "нет кофе по пути",
        "max_rent_m2": "7000",
        "preferred_distance_to_metro_m": "450",
        "confidence": "87%",
    }

    parsed = IdeaParseResponseData.model_validate(payload)

    assert parsed.business_category == "Кофейня"
    assert parsed.target_audience == ["офисные сотрудники"]
    assert parsed.location_preferences == ["рядом с метро Лубянка"]
    assert parsed.query_type == "location_search"
    assert parsed.customer_problem == "нет кофе по пути"
    assert parsed.max_rent_m2 == 7000
    assert parsed.preferred_distance_to_metro_m == 450
    assert parsed.confidence == 0.87
