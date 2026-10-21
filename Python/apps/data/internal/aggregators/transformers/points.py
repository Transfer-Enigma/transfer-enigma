def _transform_point(item):
    point, company = item
    return {
        "id": point.id,
        "company": {"id": company.id, "name": company.name},
        "ports": [],
        "translates": {
            "ru": {
                "country": point.RU_country,
                "name": point.RU_city,
            },
            "en": {
                "country": point.country,
                "name": point.city,
            },
        },
    }


def transform_points(points):
    return map(_transform_point, points)
