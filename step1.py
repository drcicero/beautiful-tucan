#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import division
import os, re, sys, warnings
from types import SimpleNamespace
import multiprocessing as mp
import utils

import sqlite_dbm as dbm # type: ignore
import mechanicalsoup as ms # type: ignore

import bs4                  # html parsing
warnings.simplefilter('ignore', UserWarning) # ignore bs4 warnings like:
# """UserWarning: "b'////////'" looks like a filename, not markup.
#    You should probably open this file and pass the filehandle into Beautiful Soup."""

from typing import List, Dict, TypeVar, Tuple, Callable, Iterable
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
  "uedates": List[str],
  "modules": List[str],
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

# achtung, tucan server nicht überlasten :)
POOLSIZE = 16 # 32  -->  ~3min

SSO_URL        = "https://www.idm.tu-darmstadt.de/idmPortal/"
TUCAN_URL      = "https://www.tucan.tu-darmstadt.de"
INFERNO_URL    = "http://inferno.dekanat.informatik.tu-darmstadt.de"
INFERNO_PREFIX = INFERNO_URL + "/pp/plans/modules/"
prefix = "cache/"

state = SimpleNamespace(
  # global variables initialized by init in maintask and subtasks:
  dbr=None, dbw=None, tucan_br=None, inferno_br=None,
  # global variables only in maintask:
  pool=None, TUCAN_START_URL=None, session_key=None
)

def init(inf_cookies: List[str], tuc_cookies: List[str]) -> None:
    pid = mp.current_process().name
    state.dbr = dbm.open(prefix + "cache", "r")       # read
    state.dbw = dbm.open(prefix + "cache" + pid, "n") # write

    state.inferno_br = ms.Browser(soup_config={"features":"lxml"})
    state.tucan_br = ms.Browser(soup_config={"features":"lxml"})
    state.inferno_br.getcached = getcached(state.inferno_br)
    state.tucan_br.getcached = getcached(state.tucan_br)
    for i in inf_cookies: state.inferno_br.get_cookiejar().set_cookie(i)
    for i in tuc_cookies: state.tucan_br.get_cookiejar().set_cookie(i)

    state.pool = None

def main() -> None:
    # ensure cache exists
    if not os.path.exists(prefix): os.mkdir(prefix)

    # merge multiple cache into one,
    #   (in case last invocation was aborted before merging).
    mergeCaches()

    # get session cookies
    credentials = {"username": utils.get_config('TUID_USER'),
                   "password": utils.get_config('TUID_PASS', is_password=True)}
    state.inferno_br = log_into_sso(credentials)
    state.tucan_br = log_into_tucan(credentials)
    inf_cookies = state.inferno_br.get_cookiejar()
    tuc_cookies = state.tucan_br.get_cookiejar()

    # init main and setup pool init
    init(inf_cookies, tuc_cookies)
    state.pool = mp.Pool(POOLSIZE, initializer=init, initargs=(inf_cookies, tuc_cookies))

    main2()

    # close databases, so they can be merged and deleted.
    state.dbr.close()
    state.dbw.close()
    state.pool.close(); state.pool.join()

    # merge multiple cache into one
    mergeCaches()

def mergeCaches() -> None:
    dct: Dict[str, str] = {}
    #print(os.listdir(prefix))
    for f in sorted(f for f in os.listdir(prefix) if f.endswith(".db")):
        print(f, end=" ")
        db = dbm.open(prefix + f[:-3], "r")
        print(len(db))
        dct.update(db)
        db.close()
    #print(os.listdir(prefix))
    db = dbm.open(prefix + "cache", "n")
    for k,v in dct.items(): db[k] = v
    db.close()
    #print(os.listdir(prefix))
    for f in sorted(f for f in os.listdir(prefix) if f.endswith(".db")):
        if not f.endswith("cache.db"): os.remove(prefix + f)

def main2() -> None:
    def json_or(x: str, f: Callable[[], X]) -> X:
        return utils.json_read_or(prefix+x, f)

    # pre-lookup
    current_semester = json_or("current_semester.json", get_current_semester)
    inferno = json_or("pre-inferno.json", lambda: download_inferno([]))
    pflicht = json_or("pre-tucan-pflicht.json", download_tucan_vv_pflicht)
    wahl    = json_or("pre-tucan-wahl.json", download_tucan_vv_wahl)
    search  = json_or("pre-tucan-search.json", lambda: download_tucan_vv_search(current_semester))

    # get courses
    course_ids = pflicht + wahl + search
    course_ids = list(sorted(set((i[0], i[1]) for i in course_ids)))
    courses    = json_or("tucan.json", lambda: download_from_tucan(course_ids))

#    # three alternative ways to get list of courses:
#    get_fbs = lambda: download_tucan_vv_catalogue(
#      ("01", "02", "03", "04", "05", "11", "13", "16", "18", "20",))
#    get_fb20 = lambda: download_tucan_vv_catalogue(("20",))
#    get_anmeldung = lambda: download_tucan_anmeldung()
#    courses2 = json_or('tucan-FBs.json',       get_fbs)
#    courses3 = json_or('tucan-FB20.json',      get_fb20)
#    courses4 = json_or('tucan-anmeldung.json', get_anmeldung)

    # get modules
    module_ids  = {module_id for course in courses
                             for module_id in course['modules']}
    module_ids |= {module_id for regulation in inferno.values()
                             for module_id in regulation.keys()}
    modules = json_or("inferno.json", lambda: download_from_inferno(module_ids))

    # computer science regulations
    modules = inner_join(courses, modules)
    for regulation in inferno.keys():
        module_part = dict()
        for k,v in modules.items():
          bsc                     = regulation.startswith("B.Sc.")
          listed_in_inferno       = k[0:10] in inferno[regulation]
          listed_in_tucan_wahl    = any(title.startswith(k) for title,url in wahl)
          listed_in_tucan_pflicht = any(title.startswith(k) for title,url in pflicht)
          linked_over_inferno     = regulation in str(v['regulations'])
          title_contains_for_inf  = any(item["title"]=="Titel" and "f\u00fcr Inf" in item["details"] for item in v["details"])

          if (listed_in_inferno
          or  listed_in_tucan_wahl
          or  linked_over_inferno
          or  (bsc and listed_in_tucan_pflicht)
          or  (bsc and title_contains_for_inf)
          ):
            module_part[k] = v
        short_regulation = "".join(c for c in regulation if c.isalnum())
        utils.json_write(prefix+'-'+short_regulation+'.json', module_part)

    if True:
        # test support for other FBs, here FB 13:
        module_part = {k:v for k,v in modules.items() if k.startswith("13-") }
        utils.json_write(prefix+'-BauUmwelt.json', module_part)

    print()

################################################################################
# download

def _download_inferno_doit(kv: Tuple[str, str, str]) -> List[Tuple[str, Dict[str, str]]]:
    formaction, k, v = kv
    print("  * ", k)
    urlopt = "?form=&regularity=" + v
    soup = state.inferno_br.getcached(INFERNO_URL + formaction + urlopt)
    toplevel = soup.select_one("#plan div > ul li")
    # group entries hierarchically
    return (k, dict(flatten_inferno(toplevel, [])))

def download_inferno(roles: List[str]) -> Dict[str, Dict[str, Tuple[str, str]]]:
    print("\ninferno")
    # make new plan, with master computer science 2015, in german
    soup = state.inferno_br.getcached(INFERNO_URL + "/pp/plans?form&lang=de")
#    lst  = (set(soup.select(".planEntry label a"))
#          - set(soup.select(".planEntry label a.inactive")))
    form = soup.form
    options = [(form['action'], i.text, i['value'])
               for i in form.select("#_regularity_id option")]
    result = dict(pMap(_download_inferno_doit, options))

    # TODO MANUAL OVERRIDES:
    result["M.Sc. IT-Sicherheit (2015)"]["20-00-0085"] = [
      "0. Pflichtveranstaltungen", "Einführung in die Kryptographie"]
    result["M.Sc. IT-Sicherheit (2015)"]["20-00-0219"] = [
      "0. Pflichtveranstaltungen", "IT-Sicherheit"]
    result["M.Sc. IT-Sicherheit (2015)"]["20-00-0581"] = [
      "0. Pflichtveranstaltungen", "Embedded System Security"]
    result["B.Sc. Informatik (2015)"]["04-00-0120"] = [
      "0. Mathe und Pflichtveranstaltungen", "Automaten, formale Sprachen und Entscheidbarkeit"]
    return result

def download_from_inferno(module_ids: Iterable[str]) -> List[str]:
    print("\nfrom inferno" +" " + str(len(module_ids)))
    return sorted(pMap(get_inferno_page, module_ids), key=lambda x: x['module_id'])

def download_from_tucan(coursetitle_url_list: List[Tuple[str, str]]) -> List[Course]:
    print("\nfrom tucan")
    return sorted(pMap(get_tucan_page, coursetitle_url_list), key=lambda x:x['title'])

def get_courses_of_semester(semester):
    soup = state.tucan_br.getcached(state.TUCAN_START_URL)
    soup = state.tucan_br.getcached(TUCAN_URL + soup.select_one('li[title="Lehrveranstaltungssuche"] a')['href'])
    form = ms.Form(soup.select_one("#findcourse"))
    form['course_catalogue'] = semester
    form['with_logo'] = '2' # we need two criteria to start search, this should show everything
    form.choose_submit("submit_search")
    page = state.tucan_br.submit(form, TUCAN_URL + form.form['action'])
    return walk_tucan_list(page.soup)

def download_tucan_vv_search(current_semester: str) -> List[Tuple[str, str]]:
    print("\ntucan-vv search")
    soup = state.tucan_br.getcached(state.TUCAN_START_URL)
    soup = state.tucan_br.getcached(TUCAN_URL + soup.select_one('li[title="Lehrveranstaltungssuche"] a')['href'])
    semester_list = [(i.text, i['value'])
                     for i in soup.select('#course_catalogue option')
                     if current_semester[0] in i.text and current_semester[1] in i.text]
    return get_courses_of_semester(semester_list[0][1])

def _walk_tucan_list_walk(_, href):
    soup = state.tucan_br.get(TUCAN_URL + href).soup
    navs = soup.select("#searchCourseListPageNavi a")

    # the last argument called ,-A00000000000000... is superflous
    # also replace the second to last argument -N3 replace by -N0
    # note: this is an optimization; if tucan changes, remove this
    clean = lambda s: ",".join(s.split(",")[:-1])
    # clean = lambda s: s

    return (
      [(i.text, clean(i['href']).replace(state.session_key, "[SESSION_KEY]"))
       for i in soup.select("a[name='eventLink']")],
      [(nav.text, nav['href']) for nav in navs] )
def walk_tucan_list(soup):
    last_link = soup.select("#searchCourseListPageNavi a")[-1]
    limit = int(last_link['class'][0].split("_", 1)[1]) # last page number
    nav = soup.select_one("#searchCourseListPageNavi .pageNaviLink_1")
    result = pCrawl(
      _walk_tucan_list_walk,
      (nav.tex, nav['href']),
      limit=limit
    )
    return list(sorted(i for lst in result.values() for i in lst))

def get_current_semester():
    print("\ntucan-vv get current semester")
    soup = state.tucan_br.getcached(state.TUCAN_START_URL)
    vv_link = soup.select_one('li[title="VV"] a')
    if vv_link == None:
      print("===============")
      print("Tucan stores your language preference on the server.")
      print("Please set tucan to german to continue.")
      print("===============")
      sys.exit()
    soup = state.tucan_br.getcached(TUCAN_URL + vv_link['href'])
    title = soup.select_one("strong")
    match = re.match(r"Vorlesungsverzeichnis des ([^ ]*)semesters? ([^ ]*) [ ]*der Technischen Universität Darmstadt", title.text)
    print(title)
    print("Semester:", match[1], match[2])
    return match[1], match[2]

def download_tucan_vv_pflicht() -> List[Tuple[str, str]]:
    print("\ntucan-vv pflicht FB20")
    soup = state.tucan_br.getcached(state.TUCAN_START_URL)
    soup = state.tucan_br.getcached(TUCAN_URL + soup.select_one('li[title="VV"] a')['href'])
    soup = state.tucan_br.getcached(TUCAN_URL + [i
        for i in soup.select("#pageContent a")
        if i.text.startswith(" FB20 - Informatik")][0]['href'])
    link = [i for i in soup.select("#pageContent a")
              if i.text.startswith(" Pflichtveranstaltungen")][0]['href']
    return walk_tucan(link)[0]

def download_tucan_vv_wahl() -> List[Tuple[str, str]]:
    print("\ntucan-vv wahl FB20")
    soup = state.tucan_br.getcached(state.TUCAN_START_URL)
    soup = state.tucan_br.getcached(TUCAN_URL + soup.select_one('li[title="VV"] a')['href'])
    soup = state.tucan_br.getcached(TUCAN_URL + [i
        for i in soup.select("#pageContent a")
        if i.text.startswith(" FB20 - Informatik")][0]['href'])
    link = [i for i in soup.select("#pageContent a")
              if i.text.startswith(" Wahlbereiche")][0]['href']
    return walk_tucan(link)[0]

#def download_tucan_vv_catalogue(FBs):
#    print("\ntucan-vv catalogue FB20")
#    soup = state.tucan_br.getcached(TUCAN_URL)
#    soup = state.tucan_br.getcached(TUCAN_URL + soup.select_one('li[title="VV"] a')['href'])
#    result = []
#    for FB in FBs:
#        link = [i for i in soup.select("#pageContent a") if i.text.startswith(" FB"+FB)][0]
#        data = walk_tucan(TUCAN_URL + link["href"]) #, limit=None if FB=="20" else limit)
#        result.extend(data)
#    return result

#def download_tucan_anmeldung():
#    print("\ntucan anmeldung david")
#    soup = state.tucan_br.getcached(TUCAN_URL)
#    link = soup.select_one('li[title="Anmeldung"] a')['href']
#    data = walk_tucan(TUCAN_URL + link)
#    return data

isParent = lambda x: "&PRGNAME=REGISTRATION"  in x or "&PRGNAME=ACTION" in x
isCourse = lambda x: "&PRGNAME=COURSEDETAILS" in x
isModule = lambda x: "&PRGNAME=MODULEDETAILS" in x
def _walk_tucan_walk(link, linki):
    soup = state.tucan_br.get(TUCAN_URL + link).soup # links is session-unique ... ?
    title = linki['title']
    path = linki['path'] + [title]
    print("\r" + "  "*len(linki['path']) + " > " + title)

    result, forks = [], []
#    if isParent(link):
    for nlink, nlinki in tucan_extract_links(soup, path):
#        if (limit is None
#        or isCourse(nlink) == (nlinki['title'][:10] in limit)):
        if   isCourse(nlink): result.append( ("course", nlinki['title'], nlink) )
        elif isModule(nlink): result.append( ("module", nlinki['title'], nlink) )
        elif isParent(nlink): forks.append( (nlink, nlinki) )
    return result, forks
#    if isCourse(link):
#        return link, get_tucan_page((title, link))
#    if isModule(link):
#        return link, merge_dict(extract_tucan_details(soup, blame=title),
#          {'modules':[title[:10]], 'title':title}) # 'link':link

def walk_tucan(start_page): # limit=None
    result = pCrawl(
      _walk_tucan_walk,
      (start_page, dict(title='', path=[])),
      limit=10
    )
    courses = ((c,d) for lst in result.values() for typ,c,d in lst if typ=="course")
    modules = ((c,d) for lst in result.values() for typ,c,d in lst if typ=="modules")
    return list(sorted(courses)), list(sorted(modules))

def flatten_inferno(item, path):
    if item and item.h2:
        path = path + [item.h2.text.replace("\t", "").replace("\n", "")]
        for item in list(item.find("ul", recursive=False).children):
            for i in flatten_inferno(item.li, path): yield i
            #yield from flatten_inferno(item.li, path)
        if item.find(class_="selectableCatalogue", recursive=False):
            catalogue = item.find(class_="selectableCatalogue", recursive=False)
            for item in catalogue.select(".planEntry label a"):
                #if 'inactive' in item['class']: continue
                yield (item.text[:10], (path[-1], item.text.split(" - ")[1])) # last path part should be enough
    else:
        pass
        # print(item)

def inner_join(courses: Iterable[Course], modules: Iterable[Module]
) -> Iterable[Module]:
    modules = {item['module_id']:item for item in modules}
    courses = ((module_id, item) for item in courses
                                 for module_id in item['modules']
                                 if module_id in modules)
    result = {k:merge_course(g, modules[k])
            for k,g in utils.groupby(courses, key=lambda x:x[0])}
    for k,v in list(result.items()):
        if len(v["details"]) < 1:
            continue

        modtitle = v["details"][1]["details"]
        if " nur Teilnahme" in modtitle:
            del result[k]
            continue

        if not (len(v["content"]) > 1
        and all(c.split(" ", 1)[0][-3:] in ["-ps","-se","-ku"]
                for c in v["content"])):
            continue

        del result[k]
        for i,c in enumerate(v["content"]):
            id,name = c.split(" ",1)
            newtitle = id + " " + modtitle + ". " + name
            newmodid = k+"-"+str(i).zfill(2)
            #print(newmodid, newtitle)
            result[newmodid] = {**v, "module_id": newmodid, "content":
              {newtitle:{**v["content"][c], "title":newtitle}} }
    return result

################################################################################
# browser

def get_inferno_page(module_id):
    soup = state.inferno_br.getcached(INFERNO_PREFIX + module_id + "?lang=de")
    details = extract_inferno_module(soup) or {}
    # TODO get title
    regulations = [i['details']
                   for i in details['details']
                   if i['title'] == "Studiengangsordnungen"]
    regulations = regulations[0] if regulations else []
    return utils.merge_dict(details, {'module_id':module_id, 'regulations':regulations})

def get_tucan_page(title_url):
    title, url = title_url

    # if the url list was stored in a previous session,
    # we need to replace the outdated session key in the url with the new one:
    soup = state.tucan_br.getcached(TUCAN_URL + url) # state.tucan_br / state.inferno_br

#    print("\n=-=-=-=-=-=-=-= BEGIN",
#          "\nwget --no-cookies --header \"Cookie: cnsc="+ state.inferno_br.get_cookiejar().get('cnsc') +"\" \"" + TUCAN_URL + url + "\" -O test.html",
#          "\n" + re.sub("[ ]+", " ", soup.text),
#          "\n=-=-=-=-=-=-=-= END")
    blame = utils.blame
    dates   = blame("no dates for '"+title+"'",   lambda: extract_tucan_dates(soup)) or []
    uedates = blame("no uedates for '"+title+"'", lambda: extract_tucan_uedates(soup, title)) or []
    details = blame("no details for '"+title+"'", lambda: extract_tucan_details(soup)) or {}
    modules = blame("no modules for '"+title+"'", lambda: extract_tucan_course_modules(soup)) or []
    return utils.merge_dict(details, {'title':title, 'dates':dates, 'uedates':uedates, 'modules':modules}) # 'link':url,

def merge_course(courses, module):
    courses = [i[1] for i in courses]

    # credits
    details = module['details']
    credits = -1
    credits_ = [i for i in details if i['title'] in ["Credit Points", "CP", "Credits"]]
    if len(credits_) > 0:
        try:
            credits = int(credits_[0]["details"].split(",")[0])
            details = [i for i in details if not i['title'] in ["Credit Points", "CP", "Credits"]]
        except:
            pass

    content = {i["title"]: {k:v for k,v in i.items() if k!="modules"} for i in courses}
    return utils.merge_dict(module, {'content':content, 'details':details, 'credits':credits})

################################################################################
# soup extractors

def tucan_extract_links(soup, path):
    def details(link): return link['href'].replace(state.session_key, "[SESSION_KEY]"), {
        'title': link.text.strip(),
        'path': path
    }
    SELECTOR = '#pageContent ul li, #pageContent table tr'
    return [details(x.a) for x in soup.select(SELECTOR) if x.a] # and x.text.strip() not in BLACKLIST

def parse_uedate(string, uetitle, blamei):
    # 'Fr, 16. Okt 2018 [13:30]-Fr, 16. Okt 2018 [13:30]' -> (day, start_hm, end_hm)
    start,  end    = string.split("-")
    s_wday, e_wday = start[:2],    end[:2]
    s_day,  e_day  = start[4:-8],  end[4:-8]
    s_hm,   e_hm   = start[-6:-1], end[-6:-1]
    if s_wday != e_wday: print("\r(warn: inequal start/end weekday for '{}' cause {} - {}"
      .format(blamei, start, end))
    return "\t".join([utils.sanitize_date(s_day), s_hm, e_hm, uetitle, utils.sanitize_date(e_day)])

def parse_dates(dates):
    def get_time(day, start, end, room):
        return "\t".join([utils.sanitize_date(day.get_text(strip=True)[4:]),
                          start.get_text(strip=True),
                          end.get_text(strip=True),
                          room.get_text(strip=True)])
    return [
        get_time(*event.find_all("td")[1:5])
        for event in dates.find_all("tr")[1:]
    ]

def extract_inferno_module(soup):
    SELECTOR = '#_title_ps_de_tud_informatik_dekanat_modulhandbuch_model_Module_id .fieldRow'
    return sanitize_details({"title":   str(i.find("label").text).strip(),
                             "details": str(i.find("div")).strip()}
                             for i in soup.select(SELECTOR))

def extract_tucan_details(soup):
    details_raw = soup.select_one('#pageContent table:nth-of-type(1) .tbdata')
    return sanitize_details({"title":   x.split('</b>')[0].strip(),
                             "details": x.split('</b>')[1].strip()}
                             for x in str(details_raw).split('<b>')[1:])

def extract_tucan_course_modules(soup):
    table = get_table_with_caption(soup, 'Enthalten in Modulen')
    if not table: return
    return list(sorted(set(i.text.strip()[:10] for i in table.select("td")[1:])))

def extract_tucan_dates(soup):
    course_dates = get_table_with_caption(soup, 'Termine')
    if not course_dates or len(course_dates.select('tr')) <= 2: return
    return parse_dates(course_dates)

def extract_tucan_uedates(soup, blamei):
    tables = soup.select('div.tb')
    if not tables: return
    course_dates = [t for t in tables if "Kleingruppe(n)" in t.select(".tbhead")[0].text]
    if not course_dates: return
    course_dates = course_dates[0]
    if not len(course_dates.select('li')): return
    return [parse_uedate(i.select('p')[2].text, i.strong.text.strip(), blamei)
            for i in course_dates.select('li') if i.select('p')[2].text.strip() != ""]

def get_table_with_caption(soup, caption):
    tables = soup.select('table.tb')
    try: return [table for table in tables if table.caption and caption in table.caption.text][0]
    except IndexError: pass

def sanitize_details(details):
    replacements = [
        ('\t', ''),
        ('<br/>', '\n'),
        ('\n', '<br/>'),
        (':', '\b'),
        ('\b', ':'),
        ('\r', ''),
        ('////', '<br/>')
    ]
    reg_replacements = [
        (r'^:', ''),
        (r']$', ''),
        (r'(<br\/>)*$', ''),
        (r'^(<br\/>)*', ''),
        (r'\s{2,}', ''),
        (r'(<br\/>)*$', '')
    ]
    details = list(details)
    for detail in details:
        detail_text = detail['details'].replace('<br/>', '////')
        detail_text = bs4.BeautifulSoup(detail_text, "html.parser").text
        detail['title'] = detail['title'].replace(':', '').strip()
        for r in replacements:
            detail_text = detail_text.replace(r[0], r[1]).strip()
        for r in reg_replacements:
            detail_text = re.sub(r[0], r[1], detail_text).strip()
        detail['details'] = detail_text

    return {'details':[i for i in details if i['details'] != ""]}

################################################################################
# helper

def _get_redirection_link(page):
    return TUCAN_URL + page.soup.select('a')[2].attrs['href']

def getcached(browser: None) -> Callable[[str], str]:
    def get(url):
        if url in state.dbw:
            soup = bs4.BeautifulSoup(state.dbw[url], "lxml")
        elif url in state.dbr:
            soup = bs4.BeautifulSoup(state.dbr[url], "lxml")
        else:
            newurl = url.replace("[SESSION_KEY]", state.session_key)
            response = browser.get(newurl)
            soup = response.soup
            if "Zugang verweigert" in soup.text:
                print(soup.text.strip())
                print("\n=== Zugang verweigert ===\n")
                browser.launch_browser(response.soup)
                print(newurl)
                assert False
            state.dbw[url] = response.content
        return soup
    return get

def anonymous_tucan():
    browser = ms.Browser(soup_config={"features":"lxml"})
    page = browser.get(TUCAN_URL)
    page = browser.get(_get_redirection_link(page)) # HTML redirects, because why not
    page = browser.get(_get_redirection_link(page))
    return browser, page

def log_into_tucan(credentials) -> ms.Browser:
    print("logging in")
    browser, page = anonymous_tucan()
    login_form = ms.Form(page.soup.select('#cn_loginForm')[0])
    login_form['usrname'] = credentials["username"]
    login_form['pass']    = credentials["password"]
    page = browser.submit(login_form, page.url)
    if not 'refresh' in page.headers:
      print(re.sub("\n+", "\n", re.sub("[ \t]+", " ", page.soup.text)))
      print("===============")
      print("This means you probably used the wrong username/password.")
      print("===============")
      sys.exit()

    print("ok")
    redirected_url = "=".join(page.headers['REFRESH'].split('=')[1:])
    page = browser.get(TUCAN_URL + redirected_url)
    page = browser.get(_get_redirection_link(page))

    state.TUCAN_START_URL = page.url
    state.session_key = page.url.split("-")[2] # "N000000000000001," == anonymous

    return browser

def log_into_sso(credentials) -> ms.Browser:
    browser = ms.Browser(soup_config={"features":"lxml"}) # html.parser
    page = browser.get(SSO_URL)
    message = page.soup.select("#msg")
    if message and not 'class="success"' in str(message): raise Exception(message[0])

    #page = browser.get(page.soup.select('meta[http-equiv="refresh"]')[0].url)
    form = ms.Form(page.soup.select('form[action="/idp/profile/cas/login?execution=e1s1"]')[0])
    #print(page.soup)
    form["j_username"] = credentials["username"]
    form["j_password"] = credentials["password"]
    #print(form, page.url)
    page = browser.submit(form, page.url)
    #print(page.soup)

    message = page.soup.select("#msg")
    if message and not 'class="success"' in str(message): raise Exception(message[0])

    return browser

def pMap(*a, **kv): return utils.progresspmap(state.pool, *a, **kv)
def pCrawl(*a, **kv): return utils.parallelCrawl(state.pool, *a, **kv)

################################################################################
# main

if __name__ == '__main__':
    main()

