import datetime
import re

import pandas as pd


def none_filter(x):
    return x if x else None


def price_filter(x):
    return (
        x if isinstance(x, (float, int))
        else float(x.replace(" ", "").replace("$", "").replace("\xa0", ""))
        if x and isinstance(x, str) and x not in ("-", "/")
        else None
    )


def cond_filter(x):
    return x if x else "COC"


def nan_to_none_mapper(x):
    return None if pd.isna(x) else x


def format_date(date_str):
    if pd.isna(date_str):
        return date_str

    ru_month_map = {
        'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04',
        'май': '05', 'июн': '06', 'июл': '07', 'авг': '08',
        'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
    }
    en_month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }

    try:
        if not isinstance(date_str, str):
            date_str = str(date_str).strip()
        else:
            date_str = date_str.strip()

        if not date_str or date_str.lower() in ['nan', 'none', 'null', '']:
            return None

        # 01-Jan-26 (DD-Mon-YY)
        if re.match(r'^\d{1,2}-[A-Za-z]{3}-\d{2}$', date_str):
            try:
                parts = date_str.split('-')
                day = parts[0].zfill(2)
                month_str = parts[1].lower()
                year_short = parts[2]

                month = en_month_map.get(month_str[:3]) or ru_month_map.get(month_str[:3])
                if not month:
                    raise ValueError(f"Unknown month: {month_str}")

                year_int = int(year_short)
                if year_int < 30:
                    year = f"20{year_short}"
                else:
                    year = f"19{year_short}"

                return f"{year}-{month}-{day}"

            except Exception as e:
                print(f"Error parsing DD-Mon-YY '{date_str}': {e}")
                return None

        # 31.01.2026 (DD.MM.YYYY)
        elif re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', date_str):
            try:
                day, month, year = date_str.split('.')
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except Exception as e:
                print(f"Error parsing DD.MM.YYYY '{date_str}': {e}")
                return None

        # 18.дек (DD.Mon) (current year)
        elif re.match(r'^\d{1,2}\.[A-Za-zа-яА-Я]{3}$', date_str, re.IGNORECASE):
            try:
                parts = date_str.split('.')
                day = parts[0].zfill(2)
                month_str = parts[1].lower()

                month = ru_month_map.get(month_str[:3]) or en_month_map.get(month_str[:3])

                if not month:
                    raise ValueError(f"Unknown month in '{date_str}'")

                current_year = datetime.date.today().year

                return f"{current_year}-{month}-{day}"

            except Exception as e:
                print(f"Error parsing DD.Mon '{date_str}': {e}")
                return None

        else:
            print(f"Unknown date format '{date_str}'")
            return None

    except Exception as e:
        print(f"Error while parsing '{date_str}': {e}")
        return None
