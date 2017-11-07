import json, re, typing as t

day_to_num = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}
num_to_day = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def json_read(path: str) -> t.Any:
    with open(path) as f: return json.load(f)

def fmt_hm(h: int, m: int) -> str:
    return str(h).zfill(2) + ":" + str(m).zfill(2)

def parse_hm(h_m: str) -> t.Tuple[int, int]:
    h, m = h_m.split(":", 1)
    return int(h), int(m)

def roman_to_latin_numbers(title: str) -> str:
    return (title
            .replace(" I ", " 1 ")
            .replace(" II ", " 2 ")
            .replace(" III ", " 3 ")
            .replace(" IV ", " 4 ")
            .replace(" V ", " 5 ")
            )

def remove_bracketed_part(title: str) -> str:
    return " ".join(re.match("([^(]*)(?:[(][^)]*[)])?(.*)", title).groups())
