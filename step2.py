import collections, itertools, json, datetime, locale, re
import bs4, pystache
from bs4.element import Tag as Bs4Tag

import utils

def main():
    now     = datetime.datetime.today() # datetime.datetime(2018, 9, 5)
    today   = now.strftime("%Y-%m")
    today2  = now.strftime("%d. %b %Y")
    today4  = utils.half_semester(now)
    prefix  = "cache/" # + utils.half_semester_filename(now) + "-"
    folder  = "gh-pages/"

    pflicht = utils.json_read(prefix + "pre-tucan-pflicht.json")
    fields  = utils.json_read(prefix + "pre-inferno.json")
    #nebenfach = utils.json_read("nebenfach.json")

#    back = utils.groupby(((course, major +" · "+ category)
#            for major,v in nebenfach.items()
#            for category,v in v.items()
#            for module in v
#            for course in module), key=lambda x:x[0])
#    back = {k:["Y Nebenfach · " + " &<br> ".join(i[1] for i in v),""] for k,v in back}
#    fields = [back] + list(fields.values())
#    print(json.dumps(fields, indent=2))

    with open("page.html")  as f: page_tmpl  = f.read()
    with open("index.html") as f: index_tmpl = f.read()
    with open("code.js")    as f: code_tmpl  = f.read()
    with open("style.css")  as f: style_tmpl = f.read()

    filename = lambda reg: "".join(c for c in reg if c.isalnum())

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

    with open(folder + "/index.html", "w") as f:
        f.write(pystache.render(index_tmpl, {
          "list": [
            {'href': href, 'title': today4 +" "+ display_regulation}
            for regulation, display_regulation, href in regulations
            if display_regulation.endswith(" Informatik")
            if not display_regulation.startswith("FB ")
          ],
          "experimentallist": [
            {'href': href, 'title': today4 +" "+ display_regulation}
            for regulation, display_regulation, href in regulations
            if not display_regulation.endswith(" Informatik")
            if not display_regulation.startswith("FB ")
          ],
          "speciallist": [
            {'href': href, 'title': today4 +" "+ display_regulation}
            for regulation, display_regulation, href in regulations
            if display_regulation.startswith("FB ")
          ],
        }))

    with open(folder + "/code.js", "w") as f:
        f.write(code_tmpl)

    with open(folder + "/style.css", "w") as f:
        f.write(style_tmpl)

    for regulation, display_regulation, href in regulations:
        print(prefix + "-" + filename(regulation) + ".json")
        dates = utils.json_read(prefix + "-" + filename(regulation) + ".json")
        data = [clean(module_id, module, fields, regulation)
                for module_id, module in dates.items()]
        data.sort(key=lambda x:(x['category'], x['id'])) # -int(x['credits'])
        with open("style.css") as f: css_style = f.read()
        js_data = json.dumps(data, indent=" ")

        with open(folder + "/" + href, "w") as f:
            f.write(pystache.render(page_tmpl, {
                "today":  today,
                "today2": today2,
                "today4": today4,
                "regulation_short": display_regulation,

                "js_data": js_data,
                "css_style": css_style,
            }))


def clean(module_id, entry, fields, regulation):
    def get_first(title: str, entry=entry):
        tmp = [detail for detail in entry["details"] if detail["title"] == title]
        return tmp[0].get('details') if len(tmp)>0 else None

    def get_abbr(title):
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
    first_entry = list(entry['content'].values())[0]
    sort_title = first_entry['title'][10:]
    _, title = sort_title.split(" ", 1)
    if len(list(entry['content'].values())) > 1:
      title = get_first("Titel") or title
    orig_title = title
    module_id = module_id or get_first("TUCaN-Nummer") or ""
    title = utils.remove_bracketed_part(title)
    title = utils.remove_bracketed_part(title)
    title = utils.roman_to_latin_numbers(title)
    title = title.replace("Praktikum in der Lehre - ", "")
    abbr = get_abbr(title)

    # reorder details
    later_titles = {
        #"Unterrichtssprache", "Sprache",
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
    early = [i for i in entry["details"] if i["title"] not in later_titles]
    late  = [i for i in entry["details"] if i["title"] in later_titles]
    entry["details"] = (
        early
      + [{"details":"<br><hr><b>Andere Angaben aus Tucan und Inferno</b><br>", "title":""}]
      + late
    )
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"
        if detail['title'] == "Studiengangsordnungen":
            regs = [(x.split("(", 1))
              for x in sorted(detail['details'].replace("<br>", "<br/>").split("<br/>"))
              if x.strip()]
            regs = utils.groupby(regs, key=lambda x:x[0])
            regs = [(k,list(v)) for k,v in regs]
#            print(detail['details'].replace("<br>", "<br/>").split("<br/>"))
#            print([ k +"("+ ", ".join(i[:-1] for _,i in v) + ")" for k,v in regs])
            detail['details'] = "<br/>".join(k+"("+", ".join(i[:-1] for _,i in sorted(v))+")" for k,v in regs) + "<br/>"

    # last name of owners
    owner = "; ".join(collections.OrderedDict(
      (x,1) for entry in entry['content'].values()
            for x in (get_first("Lehrende", entry) or
                      get_first("Modulverantwortlicher", entry) or "???").split("; ")
    ).keys()) or "???"
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
      category = category.replace("Nebenfach", "Fachübergreifend")
    else:
      category = category.replace("Pflichtveranstaltung", "Nicht einsortiert")

    # dates
    pdt   = lambda day: datetime.datetime.strptime(day, "%Y-%m-%d")
    fmtdt = lambda day: datetime.datetime.strftime(day, "%Y-%m-%d")
    shiftNweeks = lambda n, x: fmtdt(pdt(x) + datetime.timedelta(weeks=n))

    dates   = {i #+", "+ item['title'].split(" ", 1)[1]
      for item in entry['content'].values() for i in item.get('dates',   [])}
    uedates = {i for item in entry['content'].values() for i in item.get('uedates', [])}
    uebung  = "Übung " if len(uedates) != 1 else "Übungsstunde"
#    uedates = {"\t".join([shiftNweeks(i, y.split("\t",1)[0])] + y.split("\t")[1:3] + [uebung + y.split("\t")[3]]).replace(orig_title, "")
    uedates = {"\t".join([shiftNweeks(i, y.split("\t",1)[0])] + y.split("\t")[1:3] + [uebung])
               for y in uedates for i in range( int((pdt(y.split("\t")[4])
                                                    - pdt(y.split("\t")[0])).days/7+1) )}
    dates   = clean_dates( dates | uedates )

    # result
    result = utils.merge_dict(entry, dates)
    assert result['module_id'] == module_id
    del result['module_id']
    result = utils.merge_dict(result, {
        "id": module_id,
        "title": title, "title_short": abbr,
        "owner": owner, "owner_short": short_owner,
        "credits": str(entry["credits"]).zfill(2),
        'category': category,
    })
    return result


def clean_category(path):
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


def clean_dates(item):
    def parse_date(string):
      day, start, end, room = string.split("\t", 3)
      room = room.split("\t")[0]
      day   = datetime.datetime.strptime(day, "%Y-%m-%d")
      start = utils.parse_hm(start)
      end   = utils.parse_hm(end)
      return [day, start, end, room]

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
    uniqdates = {tuple(i[:4]) for i in dates}
    counted = ((i[0].weekday(), *i[1:]) for i in uniqdates)
    counted = collections.Counter(counted)
    counted = [{"count": count, "day": v[0], "start": v[1], "end": v[2],
                "room": v[3]}
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
    return { "weekly": counted, }

if __name__ == "__main__": main()

