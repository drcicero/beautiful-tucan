# coding=utf-8
import collections, itertools, json, datetime, locale, utils, re
import typing as t

import bs4, pystache
from bs4.element import Tag as Bs4Tag

locale.setlocale(locale.LC_TIME, "de_DE.UTF-8") # german month names

def from_stream(tuples: t.Iterator[t.Tuple]) -> t.Dict[t.Any, t.Any]:
    """
    Creates a nested dictionary structure, where the tuples are the path
    into the structure, and the last tuple element is the value.
    each tuple must have at least 2 components.
    example: [(1,'a'), (1,'b'), (2,3,4,'c')] --> {1:['a','b'],2:{3:{4:'c'}}}
    """
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
            # print(path, v["title"])
            yield result
        if isinstance(v["children"], list):
            yield from flatten(v["children"], path + (v["title"],))


def get_time(day: Bs4Tag, start: Bs4Tag, end: Bs4Tag, room: Bs4Tag
             ) -> t.Tuple[int, t.Tuple[int, int], t.Tuple[int, int], str, str]:
    return utils.day_to_num[day.text[:2]], utils.parse_hm(start.text), utils.parse_hm(end.text), room.get_text(strip=True), day.text[4:]


def clean(entry: t.Dict[str, t.Any]) -> t.Dict[str, str]:
    def get_first(title: str):
        tmp = [detail for detail in entry["details"] if detail["title"] == title]
        return tmp[0] if len(tmp)>0 else {}


    def clean_time(entry):
        # summarize recurring weekly events
        events = [
            get_time(*event.find_all("td")[1:5])
            for detail in entry["details"] if detail["title"] == "Kurstermine"
            for event in bs4.BeautifulSoup(detail["details"], "lxml").find_all("tr")[1:]
        ]
        sorted_dates = sorted(datetime.datetime.strptime(i[-1].replace(".", ""), "%d %b %Y")
                              for i in events)
        first_to_last = "Termine liegen von %s bis %s:<br>" % (
            sorted_dates[ 0].strftime("%d. %b"),
            sorted_dates[-1].strftime("%d. %b"),
        ) if len(sorted_dates) > 0 else ""
        weekly = [{"count": v, "time": k,
                   "start": utils.fmt_hm(*k[1]), "end": utils.fmt_hm(*k[2]),
                   "room": k[3], "day": utils.num_to_day[k[0]]}
                  for k, v in collections.Counter(i[:-1] for i in events).items()
                  if v > 1]
        weekly.sort(key=lambda a: (-a["count"], a["time"][0]))
        return first_to_last, weekly


    def get_abbr(title):
      # choose one of three abbreviations
      abbr1 = "".join(i for i in title if i.isupper() or i.isnumeric())
      abbr2 = "".join(i[0] if len(i)>0 else "" for i in title.strip().split(" "))
      abbr3 = get_first("Anzeige im Stundenplan").get("details", "").strip()
      abbrs = ([abbr3, abbr1, abbr2]
               if 1 < len(abbr3) < 6 else
               sorted((i for i in (abbr1, abbr2)), key=lambda x: abs(3.6 - len(x)))
              )
      return abbrs[0]


    # course_id, title, abbr
    title = entry["title"]
    course_id, title = title.split(" ", 1)
    title = utils.remove_bracketed_part(title)
    title = utils.remove_bracketed_part(title)
    title = utils.roman_to_latin_numbers(title)
    title = title.replace("Praktikum in der Lehre - ", "")
    abbr = get_abbr(title)

    # category
    category = entry["path"][-1]
    category = " | ".join(entry["path"])
    if "Seminare" in category and entry["credits"] == "":
        category = "Oberseminare" # seminars without credits are overseminars
    replacements = [
        # PO 2009
        ("Grundstudium", "Pflicht"),
        ("Kanonikfächer \| Kanonische Einführungsveranstaltungen", "Pflicht"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich A", "Wahl-A"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich B", "Wahl-B"),
        ("Projekte, Projektpraktika und ähnliche Veranstaltungen", "Praktika"),
        (" \| [^ ]* Prüfungsleistungen", ""),
        (" \| [^|]* \| ([ABCDEFGHJIKLMNOPQRSTUVWXYZ]*) Studienleistungen \| \\1 (.*)$", " | \\2 /// \\1 "),
        # PO 2015
        ("Pflichtbereich", "BSc Pflicht"),
        ("Wahlbereich \| Studienleistungen", "BSc Wahl"),
        ("Vorgezogene Masterleistungen \| Vorgezogene Masterleistungen der Informatik \|", "MSc"),
        ("Wahlbereich Fachprüfungen", "Wahl-A"),
        ("Wahlbereich Studienleistungen", "Wahl-B"),
        (" \(sp-FB20\)", ""),
        ("Praktika, Projektpraktika, ähnliche LV", "Praktika"),
        ("Wahlbereich \| Fachübergreifende Lehrveranstaltungen", "Fachübergreifend"),
        ("Wahlbereiche \| ", ""),
        # common
        ("Praktikum in der Lehre", "Lehrpraktika"),
        ("Praktika in der Lehre", "Lehrpraktika"),
        ("Module der ", ""),
        ("Fachübergreifend \| Gesamtkatalog aller Module des Sprachenzentrums", "Sprachzentrum"),
        (" \| ([^|]*) \| \\1", " | \\1 "),
        ("Projektpraktika", "Praktika"),
        ("Projekte", "Praktika")
    ]
    for match, result in replacements:
        category = re.sub(match, result, category)

    # reorder details
    later_titles = {
        "Modulverantwortliche",
        "Dauer",
        "Anzahl Wahlkurse",
        "Startsemester",
        "Verwendbarkeit",
        "Notenverbesserung nach §25 (2)",
        "Wahlmöglichkeiten",
        "Kurstermine",
        "Credits",
        "Anzeige im Stundenplan",
    }
    first = [i for i in entry["details"] if i["title"] not in later_titles]
    later = [i for i in entry["details"] if i["title"] in later_titles]
    entry["details"] = (
        first
      + [{"details":"<br><hr><b>Andere Angaben aus Tucan</b><br>", "title":""}]
      + later
    )
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"

    # summarize weekly recurring dates; get last name of owner
    first_to_last, weekly = clean_time(entry)
    owner = get_first("Modulverantwortliche").get("details")
    short_owner = "; ".join(i.split()[-1] for i in owner.split("; "))

    result = {
        **entry,
        "id": course_id,
        "weekly": weekly,               "first_to_last": first_to_last,
        "title": title,                 "title_short": abbr,
        "owner": owner,                 "owner_short": short_owner,
        "category": category,
        "credits": str(entry["credits"]).zfill(2),
    }
    del result["path"]
    return result


#def keyvalues(i): return (
#    list({"key": x[0], "value": keyvalues(x[1])} for x in i.items()
#         )) if isinstance(i, dict) else i


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
    if len(sys.argv) != 4:
        print("invalid command:", " ".join(sys.argv))
        print("usage:          ", " ".join([sys.argv[0], "INPUT.json", "TITLE"]))
        print("example:        ", " ".join([sys.argv[0], "python3 vv_flatten.py 2017-11-07-ws1718-bsc.json 'WS17/18 · BSc Informatik PO09' 'Liste der Kurse im Wintersemester 2017/2018 für Studierende im Studiengang 'Bachelor of Science Informatik' an der TU Darmstadt in der Prüfungsordnung von 2009' > ~/Downloads/tucan-bsc-1718.html"]))
        sys.exit()

    path  = sys.argv[1]
    title = sys.argv[2]
    title_long = sys.argv[3]

    data = utils.json_read(path)
    data = list(map(clean, flatten(data)))

    # ignore sprachzentrum or fachübergreifen courses
    data = [entry for entry in data
            if  "Sprachzentrum"    not in entry["category"]
            and "Fachübergreifend" not in entry["category"]]

    # sort inside categoryies by credits
    data = from_stream([(item["category"], item) for item in data])
    for i in data: data[i].sort(key=lambda x:(x["credits"], x["owner_short"]), reverse=True)
    data = [course for _,category in data.items() for course in category]

    #import pprint; pprint.pprint([(i["category"], i["title"]) for i in data])

    # allocate courses into weekly calendar
    grid = collections.defaultdict(lambda: set())
    for entry in data:
        for event in entry["weekly"]:
            if event["count"] <= 1: continue # remove singular events
            day, (h, m), (h2, m2), _ = event["time"]
            entry["allocated"] = allocate(grid, day, int(h * 6 + m / 10), int(h2 * 6 + m2 / 10))

    with open("code.js") as f: js_code = f.read()
    with open("style.css") as f: css_style = f.read()
    js_data = json.dumps(data, indent=" ")

    today = "03. Okt. 2017" # datetime.datetime.today().strftime("%d. %b. %Y")

#      <!--
#      <div id="details-blabla" class="details active">
#        <h1>PO Master 2015</h1>
#        Fachprüfungen (45 - 54 CP):<br>
#        + 3 oder 4 der 6 Schwerpunkte, wobei in jedem gewählten Schwerpunkt
#          mind. 6 CP erbracht werden müssen.<br>
#        <br>
#        Studienleistungen (12 - 21 CP):<br>
#        + Praktikum in der Lehre (max 1)<br>
#        + Seminare (min 1, max 2)<br>
#        + Praktika, Projektpraktika und ähnliche Veranstaltungen (min 1)<br>
#        + Außerdem ist eine Studienarbeit mit flexibler CP Anzahl möglich, wenn man ein Thema und einen Betreuer findet.<br>
#        <br>
#        Nebenfach (24 CP): (Nebenfach-Kurse werden hier nicht leider aufgezählt.)<br>
#      </div>
#      -->
#        <!-- <small>Bedenken Sie, Es ist einfacher am Anfang zu viele Kurse zu wählen und
#        dann später uninteressante Kurse aufzugeben, als zu wenige Kurse zu
#        wählen, und dann später weitere Kurse nachholen zu müssen.</small> --> 

#      <!--
#      <input type="radio" name="fishy" value="1" id="input-categories" checked> Categories<br>
#      <input type="radio" name="fishy" value="0" id="input-times"> Times
#      -->

#      <div id=fishy-times>
#        <br/><br/>

#        {{#times}}
#        <div class="time-day">  
#          {{#value}}
#          <div class="time-minute">
#            {{#value}}
#            <span class="{{marked}}" title="{{title}} · {{category}}"
#                  style=text-decoration:underline>{{title_short}}</span> 
#            {{/value}}
#          </div>
#          {{/value}}
#        </div>
#        {{/times}}
#      </div>

#      Show: 
#      <label class=inline-label for=show-selected
#        ><input type="radio" name="fishy" value="0" id="show-selected" checked>
#        Only selected courses</label>
#      <label class=inline-label for=show-courses
#        ><input type="radio" name="fishy" value="1" id="show-courses">
#        Courses</label>

    print(pystache.render("""
  <!doctype html>
  <html><head>
    <meta charset=utf8>
    <title>{{title}}</title>

    <style>
{{{css_style}}}
    </style>

  </head><body>

    <div>
      <div>
        <h1 style=margin-bottom:0>{{title}}</h1>
        <h2 style=font-size:1em;font-weight:normal;font-style:oblique;margin-top:-.5em
          >{{title_long}}</h2>
        <b>Benutzung auf eigene Gefahr!</b> Dies ist eine inoffizielle Seite.
        Es könnte sein, dass bspw. ein Kurs in nicht existiert ist oder
        eine andere Anzahl an CP bringt, die Räume geändert wurden, etc.
        Zuletzt aktualisiert: {{today}}, Daten aus {{path}}.<br/><br/>
        Es wird empfohlen jedes Semester durchschnittlich 30 CP zu machen.<br/>
      </div>
      <br/>

      <noscript>Please, activate JavaScript to use this list. Thank you. :)</noscript>
      <div id=main></div>
    </div>

    <script>
{{{js_code}}};
    </script>

    <script>
/* -------------------------------------------------------------------------- */
window.data = {{{js_data}}};
    </script>
  </body></html>

  """, {
        "title": title,
        "title_long": title_long,
        "path": path,

        "today": today,
        "js_code": js_code,
        "js_data": js_data,
        "css_style": css_style,
    }))
