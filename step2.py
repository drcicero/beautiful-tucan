import collections, itertools, json, datetime, locale, re, os
import bs4, pystache

import utils

from typing import List, Dict, Tuple, Optional, TypeVar, Set, Any
from typing_extensions import TypedDict

X = TypeVar("X")
Entry = TypedDict("Entry", {
  "details": str,
  "title": str
})
Course = TypedDict("Course", {
  "title": str,
  "details": List[Entry],
  "dates": List[str],
  "uedates": List[str]
})
Module = TypedDict("Module", {
  "content": Dict[str, Course],
  "credits": int,
  "details": List[Entry],
  "module_id": str,
  "regulations": str
})
Termin = TypedDict("Termin", {
  "count": int,
  "day": int,
  "start": Tuple[int, int],
  "end": Tuple[int, int],
  "room": str,
  "firstdate": str,
})
Module2 = TypedDict("Module2", {
  "content": Dict[str, Course],
  "weekly": List[Termin],
  "id": str,
  "title": str,
  "title_short": str,
  "owner": str,
  "owner_short": str,
  "category": str,
  "credits": int,
  "details": List[Entry],
  "regulations": str,
  "language": str,
})

def stache(x: str, y: Dict[str, Any]) -> str:
  return pystache.render(x, y) # type: ignore

def main() -> None:
    prefix   = "cache/"
    now      = datetime.datetime.today()
    time_ym  = now.strftime("%Y-%m")
    time_dmy = now.strftime("%d. %b %Y")
    semester = utils.json_read_or(prefix + "current_semester.json",
                                  lambda: "Undefined Semester")
    semester = semester[0] +" "+ semester[1]
    folder   = "gh-pages/"

    pflicht: List[Tuple[str, str]] = []
    fields: Dict[str, Dict[str, Tuple[str, str]]] = {}
    pflicht = utils.json_read_or(prefix + "pre-tucan-pflicht.json", lambda: pflicht)
    fields = utils.json_read_or(prefix + "pre-inferno.json", lambda: fields)

    #nebenfach = utils.json_read("nebenfach.json")
#    back = utils.groupby(((course, major +" · "+ category)
#            for major,v in nebenfach.items()
#            for category,v in v.items()
#            for module in v
#            for course in module), key=lambda x:x[0])
#    back = {k:["Y Nebenfach · " + " &<br> ".join(i[1] for i in v),""] for k,v in back}
#    fields = [back] + list(fields.values())
#    print(json.dumps(fields, indent=2))

    page_tmpl  = utils.file_read("page.html")
    index_tmpl = utils.file_read("index.html")
    if os.environ.get("LOGNAME") == "dave":
      code_tmpl = utils.file_read("code.orig.js")
    else:
      code_tpml = utils.file_read("dist/main.js")
    style_tmpl = utils.file_read("style.css")

    def filename(reg: str) -> str:
      return "".join(c for c in reg if c.isalnum())

    regulations = [
      (k,
       k.replace("B.Sc.", "Bachelor")
        .replace("M.Sc.", "Master")
        .replace(" (2015)", ""),
       filename(k) + ".html")
      for k in fields.keys()
      if k.endswith(" (2015)")
     ] + [
      # other FBs?
      ("BauUmwelt", "FB 13 Bau, Umwelt", "BauUmwelt.html")
    ]

    listy = [
      {'href': href, 'title': semester +" "+ display_regulation}
      for regulation, display_regulation, href in regulations
      if display_regulation.endswith(" Informatik")
      if not display_regulation.startswith("FB ")
    ]
    experimentallist = [
      {'href': href, 'title': semester +" "+ display_regulation}
      for regulation, display_regulation, href in regulations
      if not display_regulation.endswith(" Informatik")
      if not display_regulation.startswith("FB ")
    ]
    speciallist = [
      {'href': href, 'title': semester +" "+ display_regulation}
      for regulation, display_regulation, href in regulations
      if display_regulation.startswith("FB ")
    ]
    index_data = {
      "list": listy,
      "experimentallist": experimentallist,
      "speciallist": speciallist,
    }
    utils.file_write(folder + "/index.html", stache(index_tmpl, index_data))
    utils.file_write(folder + "/main.js", code_tmpl)
    utils.file_write(folder + "/style.css", style_tmpl)

    for regulation, display_regulation, href in regulations:
        print(prefix + "-" + filename(regulation) + ".json")
        modules: Dict[str, Module] = {}
        modules = utils.json_read_or(prefix + "-" + filename(regulation) + ".json",
                                     lambda: modules)
        if modules == []: continue # if file exists

        data = [clean(module_id, module, fields, regulation)
                for module_id, module in modules.items()]

        data.sort(key=lambda x: (x['category'], x['id'])) # -int(x['credits'])
        js_data = json.dumps(data, indent=1)

        page_data = {
          "today":      time_dmy,
          "semester":   semester,
          "regulation": display_regulation,
          "js_data":    js_data,
          "content":    generate_page(data)
        }
        utils.file_write(folder + "/" + href, stache(page_tmpl, page_data))

    print("finished")


def generate_page(data: List[Module2]) -> str:
    def genmodule(x: Module2) -> str: return stache("""
<div class=flex>
  <label><input id='checker-{{id}}' class=checker type=checkbox></label>
  <details class=module-wrapper>
    <summary id='module-{{id}}' class='module box-b box-b-{{id}}'>
      <span>{{credits}}cp</span>
      <span>{{title_short}}</span>
      <span title='{{title}}'>{{title}}</span>
      <span title='{{owner}}'>{{owner_short}}</span>
      <!-- <span title='{{language}}'>{{{language}}}</span> -->
      <div class=toggler-show></div>
    </summary>
    <div id='details-{{id}}' class=details>{{#details}}
      <b>{{title}}</b><br>
      {{#details}}{{{.}}}<br>{{/details}}
    {{/details}}</div>
  </details>
</div>""", x) #type: ignore

    def gencategory(title: str, modules: str) -> str: return stache("""
<details class=category>
  <summary>
    <div class=toggler-show></div>
    <b>{{title}}</b>
  </summary>
  <clear></clear>
  {{{modules}}}
</details>
<br>""", {"title": title, "modules": modules}) # type: ignore

    result = ""
    for c, modules in utils.groupby(data, lambda x: x["category"]):
      str_modules = "\n\n".join(genmodule(m) for m in modules)
      result += gencategory(c, str_modules)
    return result


def clean(module_id: str, entry: Module,
          fields: Dict[str, Dict[str, Tuple[str, str]]],
          regulation: str) -> Module2:
    def get_first(title: str, entry: List[Entry] = entry["details"]) -> Optional[str]:
        tmp = [detail for detail in entry if detail["title"] == title]
        return tmp[0].get('details') if len(tmp)>0 else None

    def get_abbr(title: str) -> str:
      # choose the best one of three abbreviations
      abbr1 = "".join(i for i in title if i.isupper() or i.isnumeric())
      abbr2 = "".join(i[0] if len(i)>0 else "" for i in title.strip().split(" "))
      abbr3 = (get_first("Kürzel") or "").strip().replace(" ", "")
      abbrs = ( [abbr3, abbr1, abbr2]
                if 1 < len(abbr3) < 6 else
                sorted((i for i in (abbr1, abbr2)), key=lambda x: abs(3.4 - len(x))) )
      #print(abbrs)
      return abbrs[0]

    # module_id, title, abbr
    courses = list(entry['content'].values())
    first_entry = courses[0]
    sort_title = first_entry['title'][10:]
    _, title = sort_title.split(" ", 1)
    if len(courses) > 1:
      title = get_first("Titel") or title
    orig_title = title
    module_id = module_id or get_first("TUCaN-Nummer") or ""
    title = utils.remove_bracketed_part(title)
    title = utils.remove_bracketed_part(title)
    title = utils.roman_to_latin_numbers(title)
    title = title.replace("Praktikum in der Lehre - ", "")
    abbr = get_abbr(title)

    # language
    mainlanguages = set(i.strip() for i in (get_first("Sprache") or "").replace(" und ", "/").replace("Deutsch", "🇩🇪").replace("Englisch", "🇬🇧").split("/"))
    sublanguages = {
      j.strip() for i in courses for j in
      ((get_first("Unterrichtssprache", i["details"])  or "").replace(" und ", "/").replace("Deutsch", "🇩🇪").replace("Englisch", "🇬🇧").split("/"))}
    language = " ".join(sorted((mainlanguages | sublanguages) - set([""])))

    # last name of owners
    owner = "; ".join(collections.OrderedDict(
      (x,1) for course in courses
            for x in (get_first("Lehrende", course["details"]) or
                      get_first("Modulverantwortlicher", course["details"]) or "???").split("; ")
    ).keys()) or "???"
    owner = owner.replace("<br>", "")
    short_owner = "; ".join(i.split()[-1] for i in owner.split("; "))

    # category
    isos = first_entry['title'].split(" ")[0].endswith("-os")
    category = fields.get(regulation, {}).get(module_id, ["",""])[0]
    category = clean_category(category)
    if category == "C. Fachübergreifende Lehrveranstaltungen": category = ""
    category = (
      "B. Oberseminare" if isos else # category == "B. Seminare" and entry["credits"] == 0
      category or {
        "01": "C. Nebenfach FB 01 (Wirtschaft & Recht; Entrepeneurship)",
        "02": "C. Nebenfach FB 02 (Philosophie)",
        "03": "C. Nebenfach FB 03 (Humanw.; Sportw.)",
        "04": "C. Nebenfach FB 04 (Logik; Numerik; Optimierung; Stochastik)",
        "05": "C. Nebenfach FB 05 (Elektrow.; Physik)",
        "11": "C. Nebenfach FB 11 (Geow.)",
        "13": "C. Nebenfach FB 13 (Bauinformatik; Verkehr)",
        "16": "C. Nebenfach FB 16 (Fahrzeugtechnik)",
        "18": "C. Nebenfach FB 18 (Elektrotechnik)",
        "41": "C. Sprachkurse",
      }.get(module_id[:2], "0. Pflichtveranstaltungen")
    )
    if "B.Sc." in regulation:
      category = category.replace("C. Nebenfach FB 04 (Logik; Numerik; Optimierung; Stochastik)", "0. Pflichtveranstaltungen")
      category = category.replace("Nebenfach", "Fachübergreifend")
      category = category.replace("0. Pflichtveranstaltungen", "0. Mathe und Pflichtveranstaltungen")
    else:
      category = category.replace("Pflichtveranstaltungen", "Nicht einsortiert")

    # dates
    def pdt(day: str) -> datetime.datetime:
      return datetime.datetime.strptime(day, "%Y-%m-%d")
    def fmtdt(day: datetime.datetime) -> str:
      return datetime.datetime.strftime(day, "%Y-%m-%d")
    def shiftNweeks(n: int, day: str) -> str:
      return fmtdt(pdt(day) + datetime.timedelta(weeks=n))

    dates   = {i for course in courses for i in course.get('dates', [])}
    uedates = {i for course in courses for i in course.get('uedates', [])}
    uebung  = "Übung " if len(uedates) != 1 else "Übungsstunde"
    uedates2 = {"\t".join(
                 [shiftNweeks(i, y.split("\t",1)[0])] +
                 y.split("\t")[1:3] +
                 [uebung]
               ) #.replace(orig_title, "")
               for y in uedates
               for i in range( int((pdt(y.split("\t")[4])
                               - pdt(y.split("\t")[0])).days/7+1) )}
    alldates = {"weekly": clean_dates(dates | uedates2)}

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
        "Titel",
    }
    early = [i for i in entry["details"] if i["title"] not in later_titles]
    late  = [i for i in entry["details"] if i["title"] in later_titles]
    entry["details"].clear()
    modul_kurs_title = "<br>".join([
      "Modul: " + module_id + " " + orig_title
    ] + [
      "Kurs: " + v['title'] for k,v in entry["content"].items()
    ])
    date_detail: List[Entry] = []
    if dates:
      firstdate = min(dates).split("\t")[0]
      lastdate  = max(dates).split("\t")[0]
      def dt2str(x: Termin) -> str:
        if x["count"] == 1:
          return "{}x {} {} {:0>2}:{:0>2} - {:0>2}:{:0>2} ({})".format(
            x["count"],
            x["firstdate"],
            utils.num_to_day[x["day"]],
            x["start"][0], x["start"][1],
            x["end"][0], x["end"][1],
            x["room"])
        return "{}x {} {:0>2}:{:0>2} - {:0>2}:{:0>2} ({})".format(
          x["count"],
          utils.num_to_day[x["day"]],
          x["start"][0], x["start"][1],
          x["end"][0], x["end"][1],
          x["room"])
      date_detail = [
        {"details": "<br>".join("* " + dt2str(i) for i in alldates["weekly"]),
         "title":"Termine zwischen " + firstdate + " und " + lastdate}]
    modul_detail: List[Entry] = [{"details":modul_kurs_title, "title":"Modul und Kurs"}]
    break_detail: List[Entry] = [{"details":"<br><hr><b>Modul: "+title+"</b><br>", "title":""}]
    entry["details"].extend(
        modul_detail
      + date_detail
      + early
      + break_detail
      + late
    )
    for k,course in entry['content'].items():
      entry["details"] += [{"details":"<br><hr><b>Kurs: "+k+"</b><br>", "title":""}]
      entry["details"] += course['details']
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"
        if detail['title'] == "Studiengangsordnungen":
            regs = [(x.split("(", 1))
              for x in sorted(detail['details'].replace("<br>", "<br/>").split("<br/>"))
              if x.strip()]
            regs2 = utils.groupby(regs, key=lambda x: x[0])
            regs3 = [(k,list(v)) for k,v in regs2]
#            print(detail['details'].replace("<br>", "<br/>").split("<br/>"))
#            print([ k +"("+ ", ".join(i[:-1] for _,i in v) + ")" for k,v in regs2])
            detail['details'] = "<br/>".join(
              k+"("+", ".join(i[:-1] for _,i in sorted(v))+")" for k,v in regs3
            ) + "<br/>"

    # result
    result = utils.merge_dict(entry, alldates) # type: ignore
    assert result['module_id'] == module_id
    del result['module_id']
    result: Module2 = utils.merge_dict(result, { # type: ignore
        "id": module_id,
        "title": title, "title_short": abbr,
        "owner": owner, "owner_short": short_owner,
        "credits": str(entry["credits"]).zfill(2),
        'category': category,
        "language": language,
    })
    return result

def clean_category(path: str) -> str:
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
    if path and not path[:3] in ["A. ", "B. ", "C. ", "0. "]:
        path = "A. " + path
    return path

def clean_dates(item: Set[str]) -> List[Termin]:
    def parse_date(string: str) -> Tuple[
        datetime.datetime, Tuple[int, int], Tuple[int, int], str]:
      day, start, end, room = string.split("\t", 3)
      room  = room.split("\t")[0]
      day   = datetime.datetime.strptime(day, "%Y-%m-%d")
      start = utils.parse_hm(start)
      end   = utils.parse_hm(end)
      return day, start, end, room

    dates = list(sorted(parse_date(i) for i in item))

#    # first, last event
#    first = last = first_to_last = ""
#    if len(dates) > 0:
#        first = dates[ 0][0].strftime("%Y-%m-%d")
#        last  = dates[-1][0].strftime("%Y-%m-%d")
#        first_to_last = "Termine liegen von %s bis %s:<br>" % (
#            dates[ 0][0].strftime("%d. %b"),
#            dates[-1][0].strftime("%d. %b"),
#        )

    # how many weeks does the event repeat?
    uniqdates = {i[:4] for i in dates}
    counted = [(i[0].weekday(), *i[1:]) for i in uniqdates]
    counted = collections.Counter(counted)
    counted: List[Termin] = [
      {"count": count, "day": v[0], "start": v[1], "end": v[2], "room": v[3],
       "firstdate": ""}
       for v, count in counted.items()]

    # add rooms of weekly events together
    for d in counted:
#        roomlst = [room for i in dates
#                        if (i[0].weekday(), i[1], i[2]) ==
#                           (d['day'], d['start'], d['end'])
#                        for room in i[3].split(",")]
#        d['room']  = ", ".join(sorted(set(roomlst)))
        d['firstdate'] = min(i[0] for i in dates
                                  if (i[0].weekday(), i[1], i[2]) ==
                                     (d['day'], d['start'], d['end'])).strftime("%Y-%m-%d")

    counted.sort(key=lambda a: (a["firstdate"], a["start"]))
    return counted

if __name__ == "__main__": main()
