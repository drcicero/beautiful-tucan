# coding=utf-8
import collections
import itertools
import json
import datetime
import typing as t
import locale
import utils

import bs4
import pystache
from bs4.element import Tag as Bs4Tag

locale.setlocale(locale.LC_TIME, "de_DE.UTF-8") # german month names

def from_stream(tuples: t.Iterator[t.Tuple]) -> t.Dict[t.Any, t.Any]:
    """ creates a nested dictionary structure, where the tuples are the path into the structure, and the last tuple element is the value.
    each tuple must have at least 2 components.
    example: [(1,'a'), (1,'b'), (2,3,4,'c')] --> {1:['a','b'],2:{3:{4:'c'}}} """
    result = collections.OrderedDict()
    for t in tuples:
        thing = result
        for k in t[:-2]:
            if k not in thing: thing[k] = collections.OrderedDict()
            thing = thing[k]
        if len(t) >= 2 and t[-2] not in thing: thing[t[-2]] = []
        thing[t[-2]].append(t[-1])
    return result


def flatten(it, path: t.Tuple[str, ...] = ()) -> t.Iterable[t.Dict[str, t.Any]]:
    for k, v in enumerate(it):
        if "details" in v:
            result = {"path": path, **v}
            del result["children"]
#            print(path, v["title"])
            yield result
        if isinstance(v["children"], list):
            yield from flatten(v["children"], path + (v["title"],))


def adapt(entry: t.Dict[str, t.Any]) -> t.Dict[str, str]:
    def get_first(title: str):
        tmp = [detail for detail in entry["details"] if detail["title"] == title]
        return tmp[0] if len(tmp)>0 else {}

    # remove redundancies from title and category; create unique id
    category = entry["path"][-1]
    title = utils.roman_to_latin_numbers(entry["title"])
    courss_id = title[:title.index(" ")]  # get id
    title = title[title.index(" ") + 1:] # remove id from title
    title = utils.remove_bracketed_part(utils.remove_bracketed_part(title)) # remove up to two brackets
    force_ignore = False
    if not force_ignore and len(entry["path"]) > 1: # > 2 and entry["path"][-2].endswith("Studienleistungen"):

        PIDL = "Praktikum in der Lehre - "
        if PIDL in title:
            title = title.replace(PIDL, "")
            category = "Praktika in der Lehre"

        if False:
            title = category[:category.index(" ") + 1] + title
            category = category[category.index(" ") + 1:]

#        if category not in ("Praktika in der Lehre", "Seminare"):
#            category = "Praktika, Projektpraktika und ähnliche Veranstaltungen"
        # if entry["credits"] == "": print(category)
        if category.startswith("Seminare") and entry["credits"] == "":
            category = "Oberseminare"
        if "Gesamtkatalog aller Module des Sprachenzentrums" in entry["path"]:
            category = "Sprachzentrum · " + category
        else:
            category = entry["path"][1] + " · " + category

        category = ( category
          .replace("Vorgezogene Masterleistungen der Informatik", "Master")
          .replace("Praktika, Projektpraktika, ähnliche LV", "Praktika")
          .replace("Projekte, Projektpraktika und ähnliche Veranstaltungen", "Praktika")
          .replace("Module der ", "")
        )

#        print(category, "|", title)
    else:
        category = "Bachelor · " + category
    category = category.split(" · ", 1)
    category = category[0].replace(" ", "-") +" · "+ category[1]
    # course_id = "".join(c for c in (category + "-" + title.replace(" ", "-")).lower() if c=="-" or c.isalnum())

    # summarize recurring weekly events
    def get_time(day: Bs4Tag, start: Bs4Tag, end: Bs4Tag, room: Bs4Tag
                 ) -> t.Tuple[int, t.Tuple[int, int], t.Tuple[int, int], str, str]:
        return utils.day_to_num[day.text[:2]], utils.parse_hm(start.text), utils.parse_hm(end.text), room.get_text(strip=True), day.text[4:]
    events = [
        get_time(*event.find_all("td")[1:5])
        for detail in entry["details"] if detail["title"] == "Kurstermine"
        for event in bs4.BeautifulSoup(detail["details"], "lxml").find_all("tr")[1:]
    ]
    sorted_dates = sorted(datetime.datetime.strptime(i[-1].replace(".", ""), "%d %b %Y") for i in events)
    first_to_last = "Termine liegen von %s bis %s:<br>" % (
        sorted_dates[ 0].strftime("%d. %b"),
        sorted_dates[-1].strftime("%d. %b"),
    ) if len(sorted_dates) > 0 else ""
    clean_time = [{"count": v, "time": k, "start": utils.fmt_hm(*k[1]), "end": utils.fmt_hm(*k[2]), "room": k[3], "day": utils.num_to_day[k[0]]}
                  for k, v in collections.Counter(i[:-1] for i in events).items()
                  if v > 1]
    clean_time.sort(key=lambda a: (-a["count"], a["time"][0]))

    # choose one of three abbreviations
    abbr1 = "".join(i for i in title if i.isupper() or i.isnumeric())
    abbr2 = "".join(i[0] if len(i)>0 else "" for i in title.strip().split(" "))
    abbr3 = get_first("Anzeige im Stundenplan").get("details", "").strip()
    abbr = [abbr3, abbr1, abbr2] if 1 < len(abbr3) < 6 else sorted((i for i in (abbr1, abbr2)), key=lambda x: abs(3.6 - len(x)))
    # print(abbr) # print all possible abbrs, first was chosen
    abbr = abbr[0]

    # get owner and last name of owner
    owner = get_first("Modulverantwortliche").get("details")
    short_owner = "; ".join(i.split()[-1] for i in owner.split("; "))

    # reorder description
    later = [i for i in entry["details"] if i["title"] in {
        "Dauer",
        "Anzahl Wahlkurse",
        "Startsemester",
        "Verwendbarkeit",
        "Notenverbesserung nach §25 (2)",
        "Wahlmöglichkeiten",
        "Kurstermine",
    }]
    entry["details"] = [
        detail for detail in entry["details"]
        if detail not in later and
           detail["title"] not in {
               # "Modulverantwortliche",
               "Credits",
               "Anzeige im Stundenplan",
           }
    ] + [{"details":"<br><hr><b>Andere Angaben aus Tucan</b><br>", "title":""}] + later
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"

    result = {
        **entry,
        "id": courss_id, "abbr": abbr, "title": title,
        "clean_time": clean_time, "first_to_last": first_to_last,
        "owner": owner, "short_owner": short_owner,
        "category": category,
        "credits": str(entry["credits"]).zfill(2),
    }
    del result["path"]
    return result


def keyvalues(i): return (
    list({"key": x[0], "value": keyvalues(x[1])} for x in i.items()
         )) if isinstance(i, dict) else i


AllocationDict = t.Dict[t.Tuple[int, int], t.Set[int]]
def allocate(grid: AllocationDict, day: int, min_t: int, max_t: int) -> int:
    """ add a unused number to the cells (day, min_t) to (day, mint_t + dt) of grid, and return it. """
    for id in itertools.count():
        if all(id not in grid[(day, t)] for t in range(min_t, max_t)):
            for t in range(min_t, max_t): grid[(day, t)].add(id)
            return id


def pipe(init, *args):  # destroys typing info :/ , should better be a macro
    value = init
    for f in args: value = f(value)
    return value


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("invalid command:", " ".join(sys.argv))
        print("usage:          ", " ".join([sys.argv[0], "INPUT.json", "TITLE"]))
        print("example:        ", " ".join([sys.argv[0], "ws1718-msc.json", "'TUDA VV MSc Informatik PO2015 WiSe 17/18'"]))
        sys.exit()

    path  = sys.argv[1]
    title = sys.argv[2]

    data = utils.json_read(path)
    data = list(map(adapt, flatten(data)))

    grid = collections.defaultdict(lambda: set())

    # consider only prüfungsleistungen / vorlesungen for calendar
    data = [entry for entry in data
            if "Prüfungsleistungen" not in entry["category"]]

    for entry in data:
        for event in entry["clean_time"]:
            # remove singular events
            if event["count"] <= 1: continue
            day, (h, m), (h2, m2), _ = event["time"]
            entry["allocated"] = allocate(grid, day, int(h * 6 + m / 10), int(h2 * 6 + m2 / 10))

    categories = from_stream([item["category"].split(" · ", 1) + [item] for item in data])
    for i in categories:
        for j in categories[i]:
            categories[i][j].sort(key=lambda x:x["credits"], reverse=True)
    categories = list(keyvalues(categories))

    # import pprint; pprint.pprint(categories)

    js_data = json.dumps(data, indent=" ")
    with open("code.js") as f: js_code = f.read()

    with open("style.css") as f: css_style = f.read()

    today = "03. Okt. 2017" # datetime.datetime.today().strftime("%d. %b. %Y")

    print(pystache.render("""
  <!doctype html>
  <html><head>
    <meta charset=utf8>
    <title>{{title}}</title>

    <style>
{{{css_style}}}
    </style>

    </script>
  </head><body>

    <div class="half" style="position: fixed;right: 0;height: calc(100vh - 2em);overflow-x:none;overflow-y:scroll;">
      <!--
      <div id="details-blabla" class="details active">
        <h1>PO Master 2015</h1>
        Fachprüfungen (45 - 54 CP):<br>
        + aus 3 oder 4 der 6 Schwerpunkte des Fachbereichs Informatik,
        wobei in jedem gewählten Schwerpunkt mind. 6 CP erbracht werden müssen.<br>
        <br>
        Studienleistungen (12 - 21 CP):<br>
        + Praktikum in der Lehre (max 1)<br>
        + Seminare (min 1, max 2)<br>
        + Praktika, Projektpraktika und ähnliche Veranstaltungen (min 1)<br>
        + Außerdem ist eine Studienarbeit mit flexibler CP Anzahl möglich, wenn man ein Thema und einen Betreuer findet.<br>
        <br>
        Nebenfach (24 CP): (Nebenfach-Kurse werden hier nicht aufgezählt.)<br>
      </div>
      -->
        <!-- <small>Bedenken Sie, Es ist einfacher am Anfang zu viele Kurse zu wählen und
        dann spöter uninteressante Kurse aufzugeben, als zu wenige Kurse zu
        wählen, und dann später weitere Kurse nachholen zu müssen.</small> --> 

      {{#categories}}
      {{#value}}
      {{#value}}
      <div id="details-{{id}}" class="details">
        <h1>{{title}}</h1>
        {{{first_to_last}}}
        {{#clean_time}}<i>× {{count}} mal {{day}}, {{start}}-{{end}} in {{room}}</i><br>{{/clean_time}}
        {{#details}}
          <p><b>{{title}}</b><br>{{{details}}}</p>
        {{/details}}
      </div>
      {{/value}}
      {{/value}}
      {{/categories}}
    </div>

    <div class="half">
      <div>
        <h1>{{title}}</h1>
        <b>Benutzung auf eigene Gefahr!</b> Dies ist eine inoffizielle Seite.
        Es könnte sein, dass bspw. ein Kurs in ihrer PO nicht wählbar ist oder
        eine andere Anzahl an CP bringt, die Räume geändert wurden, etc.
        Zuletzt aktualisiert: {{today}}, Daten aus {{path}}.<br>
        <br>
        Es wird empfohlen jedes Semester durchschnittlich 30 CP zu machen.<br>
      </div>
      <br/>

      <!--
      <input type="radio" name="fishy" value="1" id="input-categories" checked> Categories<br>
      <input type="radio" name="fishy" value="0" id="input-times"> Times
      -->

      {{#categories}}
        <input type="radio" name="supercategory" value="{{key}}" id="tab-{{key}}" class="tab-input" hidden>
        <label for="{{key}}" class="tab">{{key}}</label>
      {{/categories}}

      <div id=fishy-categories>
        {{#categories}}
        <div class="supercategory" id="supercategory-{{key}}">{{key}}<br>
        {{#value}}
        <div class="category">::: {{key}}</div>
        {{#value}}
        <div class="input-item">
          <input class="input" type="checkbox" id="input-{{id}}"/>
          <label for="input-{{id}}"></label>
          <div class="item" id="item-{{id}}">
            <span style="color:red">{{credits}} CP</span> · 
            <span>{{abbr}} · {{title}}</span>
            <small>{{short_owner}} · {{#clean_time}}{{count}}x {{day}}, {{/clean_time}}</small>
          </div>
        </div>
        {{/value}}
        {{/value}}
        </div>
        {{/categories}}
      </div>

      <div id=fishy-times>
        <br/><br/>

        {{#times}}
        <div class="time-day">  
          {{#value}}
          <div class="time-minute">
            {{#value}}
            <span class="{{marked}}" title="{{title}} · {{category}}"
                  style=text-decoration:underline>{{abbr}}</span> 
            {{/value}}
          </div>
          {{/value}}
        </div>
        {{/times}}
      </div>

      <button id=remove_unchecked>Remove unchecked courses</button>
      <button id=show_all>Show all courses</button>
      <br>
      <br>
    </div>

    <script>
/* -------------------------------------------------------------------------- */
var data = {{{js_data}}};
    </script>

    <script>
/* -------------------------------------------------------------------------- */
{{{js_code}}};
    </script>
  </body></html>

  """, {
        "title": title,
        "today": today,
        "path": path,
        "categories": categories,
        "js_code": js_code,
        "js_data": js_data,
        "css_style": css_style,
    }))
