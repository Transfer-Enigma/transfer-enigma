import re


def validate_name(dict_data, name):
    if "(" in name:
        name = re.sub(r"\(.*\)", "", name)

    name = name.strip()
    if (
        name in dict_data
        or ("," not in name and " " not in name or name.count(" ") < 2)
        and "-" not in name
    ):
        return name

    country_and_name = name.split(", ", 1)
    if "-" in country_and_name[-1]:
        country_and_name[-1] = country_and_name[-1].replace("-", " ")
    else:
        country_and_name[-1] = country_and_name[-1].replace(" ", "-")
    new_name = ", ".join(country_and_name)
    if new_name in dict_data:
        return new_name

    return name


def union_country_and_name(dict_data, country, name):
    if country and name:
        return validate_name(dict_data, country.upper() + ", " + name)
    return validate_name(dict_data, name) or country
