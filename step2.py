import collections, itertools, json, datetime, locale, re
import utils
import typing as t

import bs4, pystache
from bs4.element import Tag as Bs4Tag

locale.setlocale(locale.LC_TIME, "de_DE.UTF-8") # german month names

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
    return (utils.day_to_num[day.text[:2]],
            utils.parse_hm(start.text),
            utils.parse_hm(end.text),
            room.get_text(strip=True),
            day.text[4:])


def simplify_path(path):
    replacements = [
        # PO 2009
        ("Grundstudium", "Pflicht"),
        ("Kanonikfächer \| Kanonische Einführungsveranstaltungen", "Pflicht"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich A", "Wahl-A"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich B", "Wahl-B"),
        ("Projekte, Projektpraktika und ähnliche Veranstaltungen", "B. Praktika"),
        (" \| [^ ]* Prüfungsleistungen", ""),
        (" \| [^|]* \| ([A-Z]*) Studienleistungen \| \\1 (.*)$", " | \\2 /// \\1 "),
        # PO 2015
        ("Pflichtbereich", "BSc Pflicht"),
        ("Wahlbereich \| Studienleistungen", "BSc Wahl"),
        ("Vorgezogene Masterleistungen \| Vorgezogene Masterleistungen der Informatik \|", "MSc"),
        ("Wahlbereich Fachprüfungen", "Wahl-A"),
        ("Wahlbereich Studienleistungen", "Wahl-B"),
        (" \(sp-FB20\)", ""),
        ("Praktika, Projektpraktika, ähnliche LV", "B. Praktika"),
        ("Praktika, Projektpraktika und ähnliche Veranstaltungen", "B. Praktika"),
        ("Fachübergreifende Lehrveranstaltungen", "C. Fachübergreifende Lehrveranstaltungen"),
        ("Wahlbereiche \| ", ""),
        # common
        ("Praktika in der Lehre", "B. Praktika in der Lehre"),
        ("Praktikum in der Lehre", "B. Praktika in der Lehre"),
        ("Module der ", ""),
        ("Fachübergreifend \| Gesamtkatalog aller Module des Sprachenzentrums", "Sprachzentrum"),
        (" \| ([^|]*) \| \\1", " | \\1 "),
        ("Projektpraktika", "X Praktika"),
        ("Projekte", "B. Praktika"),
        ("Seminare", "B. Seminare")
    ]
    for match, result in replacements:
        path = re.sub(match, result, path)
    if path and not path[:3] in ["A.", "B. ", "C. "]:
        path = "A. " + path
    return path


def clean(module_id: str, entry: t.Dict[str, t.Any], fields, regulation) -> t.Dict[str, str]:
    def get_first(title: str, entry=entry):
        tmp = [detail for detail in entry["details"] if detail["title"] == title]
        return tmp[0].get('details') if len(tmp)>0 else None

    def get_abbr(title):
      # choose the best one of three abbreviations
      abbr1 = "".join(i for i in title if i.isupper() or i.isnumeric())
      abbr2 = "".join(i[0] if len(i)>0 else "" for i in title.strip().split(" "))
      abbr3 = (get_first("Anzeige im Stundenplan") or "").strip()
      abbrs = ([abbr3, abbr1, abbr2]
               if 1 < len(abbr3) < 6 else
               sorted((i for i in (abbr1, abbr2)), key=lambda x: abs(3.6 - len(x)))
              )
      return abbrs[0]

    # module_id, title, abbr
    sort_title = entry['content'][0]['title'][10:]
    sort, title = sort_title.split(" ", 1)
    title = title or get_first("Titel") or ""
    module_id = module_id or get_first("TUCaN-Nummer") or ""
    title = utils.remove_bracketed_part(title)
    title = utils.remove_bracketed_part(title)
    title = utils.roman_to_latin_numbers(title)
    title = title.replace("Praktikum in der Lehre - ", "")
    abbr = get_abbr(title)

    # reorder details
    later_titles = {
        "Unterrichtssprache", "Sprache",
        "Min. | Max. Teilnehmerzahl",

        "TUCaN-Nummer", "Kürzel", "Anzeige im Stundenplan", # "Titel",
        "Lehrveranstaltungsart", "Veranstaltungsart",
        "Turnus", "Startsemester",
        "SWS", "Semesterwochenstunden",
        "Diploma Supplement",
        "Modulausschlüsse", "Modulvoraussetzungen",
        "Studiengangsordnungen", "Verwendbarkeit", "Anrechenbar für",
        "Orga-Einheit", "Gebiet", "Fach",
        "Modulverantwortliche", # "Lehrende",

        "Dauer",
        "Anzahl Wahlkurse",
        "Notenverbesserung nach §25 (2)",
        "Wahlmöglichkeiten",
        "Credits",
        "Kurstermine",
    }
    first = [i for i in entry["details"] if i["title"] not in later_titles]
    later = [i for i in entry["details"] if i["title"] in later_titles]
    entry["details"] = (
        first
      + [{"details":"<br><hr><b>Andere Angaben aus Tucan und Inferno</b><br>", "title":""}]
      + later
    )
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"
        if detail['title'] == "Studiengangsordnungen":
            detail['details'] = detail['details'].replace("<br/><br/>", "<br/>")

    #get last name of owner
    import collections as col
    owner = "; ".join(col.OrderedDict(
      (x,1) for entry in entry['content']
            for x in (get_first("Lehrende", entry) or
            get_first("Modulverantwortliche", entry)).split("; ")
    ).keys()) or "???"
    short_owner = "; ".join(i.split()[-1] for i in owner.split("; "))

    simplified_path = simplify_path(fields['M.Sc. Informatik (2015)'].get(module_id, ["",""])[0])
    category = (
#      get_first("Gebiet") or get_first("Orga-Einheit") or get_first("Veranstaltungsart") or
      "B. Oberseminare"
      if simplified_path == "B. Seminare" and entry["credits"] == 0 else
      simplified_path
      or
      {
        "01": "C. Nebenfach FB Entrep",
        "02": "C. Nebenfach FB Philosophie",
        "03": "C. Nebenfach FB Humanw, Sportw",
        "04": "C. Nebenfach FB Logik, Numerik, Optimierung, Stochastik",
        "11": "C. Nebenfach FB Geow",
        "13": "C. Nebenfach FB Bau, Verkehr",
        "16": "C. Nebenfach FB Fahrzeug",
        "18": "C. Nebenfach FB Elektro",
        "05": "C. Nebenfach FB Elektro, Physik",
        "41": "C. Sprachkurse",
      }.get(module_id[:2]) or
      "0. Pflichtveranstaltungen"
    )
    if "B.Sc." in regulation:
      category = category.replace("Nebenfach", "Fachübergreifend")

    dates = clean_dates(item['dates'] for item in entry['content'] if 'dates' in item)
    result = {
        **entry, **dates,
        "id": module_id,
        "title": title, "title_short": abbr,
        "owner": owner, "owner_short": short_owner,
        "credits": str(entry["credits"]).zfill(2),
        'category': category,
    }
#    del result["path"]
    return result


#def keyvalues(i): return (
#    list({"key": x[0], "value": keyvalues(x[1])} for x in i.items()
#         )) if isinstance(i, dict) else i


#AllocationDict = t.Dict[t.Tuple[int, int], t.Set[int]]
#def allocate(grid: AllocationDict, event, day: int, min_t: int, max_t: int) -> int:
#    """ add a unused number to the cells (day, min_t) to (day, mint_t + dt) of grid, and return it. """
#    for id in itertools.count():
#        if all(id not in grid[str(day)+"-"+str(t)] for t in range(min_t, max_t)):
#            for t in range(min_t, max_t):
#                grid[str(day)+"-"+str(t)][id] = event
#            return id

import datetime
def clean_dates(item):
    dates = [i.split("\t") for lst in item for i in lst]
    # summarize recurring weekly events
    sorted_dates = list(sorted(datetime.datetime.strptime(i[0].replace(".", ""), "%d %b %Y")
                               for i in dates))
    first = last = first_to_last = ""
    if len(sorted_dates) > 0:
      first = sorted_dates[ 0].strftime("%Y-%m-%d")
      last  = sorted_dates[-1].strftime("%Y-%m-%d")
      first_to_last = "Termine liegen von %s bis %s:<br>" % (
          sorted_dates[ 0].strftime("%d. %b"),
          sorted_dates[-1].strftime("%d. %b"),
      )

    weekly = [{"count": v,
               "time": [utils.day_to_num[k[0]], utils.parse_hm(k[1]), utils.parse_hm(k[2])],
               "day": k[0], "start": k[1], "end": k[2]}
              for k, v in collections.Counter((i[1],i[2],i[3]) for i in dates).items()
              if v > 1]
    for d in weekly:
      roomlst = [room for i in dates
                      if (i[1], i[2], i[3]) == (d['day'], d['start'], d['end'])
                      for room in i[4].split(",")]
      d['room'] = ", ".join(set(roomlst))
    weekly.sort(key=lambda a: (-a["count"], a["time"][0]))
    return {
        "weekly": weekly, "first_to_last": first_to_last,
        "first": first, "last": last,
        "dates": dates,
    }

def pipe(init, *args):  # destroys typing info :/ , should better be a macro
    value = init
    for f in args: value = f(value)
    return value

def groupby(iterator, key):
    import itertools
    lst = sorted(iterator, key=key)
    return itertools.groupby(lst, key)

if __name__ == "__main__":
    import sys

    now      = datetime.datetime.today() # datetime.datetime(2018, 8, 11)
    filedate = now.strftime("%Y-%m-%d")
    today    = now.strftime("%Y-%m")
    today2   = now.strftime("%d. %b %Y")
    today3   = now.strftime("%b %Y")
    today4   = ("Sommer" if 3 <= now.month < 9 else "Winter") +" "+ now.strftime("%Y")

    fields    = utils.json_read("cache/" + filedate + "-inferno.json")
    #nebenfach = utils.json_read("nebenfach.json")
    #dates     = utils.json_read("cache/18-dates.json")
    #details   = utils.json_read("cache/18-details.json")

#    back = groupby(((course, major +" · "+ category)
#            for major,v in nebenfach.items()
#            for category,v in v.items()
#            for module in v
#            for course in module), key=lambda x:x[0])
#    back = {k:["Y Nebenfach · " + " &<br> ".join(i[1] for i in v),""] for k,v in back}
#    fields = [back] + list(fields.values())
#    print(json.dumps(fields, indent=2))


    for regulation in ["B.Sc. Informatik (2015)", "M.Sc. Informatik (2015)"]:
        filename = "".join(c for c in regulation if c.isalnum())
        dates = utils.json_read("cache/" + filedate + "--" + filename + ".json")

        data = [clean(module_id, module, fields, regulation)
                for module_id, module in dates.items()]
        data.sort(key=lambda x:(x['category'], x['id'])) # -int(x['credits'])
        with open("style.css") as f: css_style = f.read()
        js_data = json.dumps(data, indent=" ")

    #      <!--
    #      <div id="details-blabla" class="details active">

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

    #    name = field.replace(".", "").replace("(", "").replace(")", "").replace("/", "").replace(" ", "")

        #today = datetime.datetime.today().strftime("%d. %b. %Y")
        with open("gh-pages/" + today + "-" + filename + ".html", "w") as f:
            f.write(pystache.render("""
          <!doctype html>
          <html><head>
            <meta charset=utf8>
            <meta name=viewport content="width=device-width, initial-scale=1.0">
            <title>{{today4}}, {{regulation}}, inoffizielles Wochenplaner TU Darmstadt FB Informatik</title>
            <style>
        {{{css_style}}}
            </style>

          </head><body>

            <div>
              <h1>{{today4}}, {{regulation}}</h1>
              <p>Zuletzt aktualisiert: {{today2}}</p>
              <p>
<h2 style=font-size:1em;font-weight:bold
><span style=color:red>inoffizielles</span> Vorlesungsverzeichnis TU Darmstadt FB Informatik</h2>
<b>Benutzung auf eigene Gefahr!</b>
Dies ist eine inoffizielle Seite.
Beachten Sie, das Übungsgruppentermine nicht aufgeführt werden, sondern nur Termine die in Tucan direkt als Veranstaltungstermin gelistet sind. Manchmal finden Termine auch erst ab der zweiten Woche statt.
Desweiteren kann es sein, dass bspw. ein Kurs in der falschen Kategorie angezeigt wird (wie bspw. 'Mathe 3'), ein Kurs fehlt, oder ein angezeigter Kurs eine andere Anzahl an CP bringt, die Räume geändert wurden, etc.
              </p>
              <!--<p>Hinweis: Pflichtveranstaltung müssen irgendwann belegt worden sein, aber nicht unbedingt alle gleichzeitig.
              Für Regelstudienzeit sind durchschnittlich jedes Semester 30 CP vorgesehen.-->
              <a href=./index.html>Mehr Informationen</a></p>
              </details>
            </div>
            <br/>
            <noscript>Please, activate JavaScript to use this list. Thank you. :)</noscript>
            <div id=main></div>
            <div id=main2></div>

            <script src="code.js"></script>

            <script>
        /* -------------------------------------------------------------------------- */
        window.data = {{{js_data}}};
            </script>
          </body></html>

          """, {
                "today": today,
                "today2": today2,
                "today3": today3,
                "today4": today4,
                "regulation": regulation[:-7],

                "today": today,
                "js_data": js_data,
                "css_style": css_style,
            }))

