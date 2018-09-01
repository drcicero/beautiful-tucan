#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import division
import os, re, sys, json, getpass, warnings, itertools, datetime, time, traceback
import multiprocessing.dummy as mp

import bs4                  # html parsing
import mechanicalsoup as ms # GET, POST, cookie requests

POOLSIZE = 8 #  8  -->  ~6min; 

SSO_URL     = "https://sso.tu-darmstadt.de"
TUCAN_URL   = "https://www.tucan.tu-darmstadt.de"
INFERNO_URL = "http://inferno.dekanat.informatik.tu-darmstadt.de"

# do not follow these links to decrease run time
BLACKLIST = (
    # anmeldung
    'Weitere Veranstaltungen',
    'Leistungen für den Masterstudiengang',  # PO 2009
    'Vorgezogene Masterleistungen',          # PO 2015
    'Anmelden',
    'Zusätzliche Leistungen',
    'Gesamtkatalog aller Module an der TU Darmstadt',
    'Informatik fachübergreifend',
    'Module des Sprachenzentrums mit Fachprüfungen',
    'Fachübergreifende Veranstaltungen',     # PO 2009
    'Fachübergreifende Lehrveranstaltungen', # PO 2015
    'Veranstaltung',

    # vorlesungsverzeichnis
    'Gesamtes Lehrangebot',
    'Computational Engineering (Studiengang)',
    'Lehramt',
    'Service für andere Fachbereiche',
    'Prüfungstermine',
)

warnings.simplefilter('ignore', UserWarning) # ignore bs4 warnings like:
# """UserWarning: "b'////////'" looks like a filename, not markup.
#    You should probably open this file and pass the filehandle into Beautiful Soup."""


def main():
    if not os.path.exists('cache'): os.mkdir("cache")

    prefix = datetime.datetime.today().strftime("cache/%Y-%m-%d-")
    regulations = [
      "M.Sc. Informatik (2015)",
      "B.Sc. Informatik (2015)",
    ]

    cred = get_credentials()

    inferno = json_read_or(prefix+'inferno.json', lambda: download_inferno(cred, regulations))
    courses = json_read_or(prefix+'pre-tucan.json', lambda: download_tucan_vv_search(cred))
    courses = json_read_or(prefix+'tucan.json', lambda: download_tucan_vv_pages(cred, courses))

    # three alternative ways to get list of courses:
    courses2 = [] #json_read_or(prefix+'tucan-FBs.json', lambda: download_tucan_vv_catalogue(cred, ("01", "02", "03", "04", "05", "11", "13", "16", "18", "20",)))
    courses3 = [] #json_read_or(prefix+'tucan-FB20.json', lambda: download_tucan_vv_catalogue(cred, ("20",)))
    courses4 = [] #json_read_or(prefix+'tucan-anmeldung.json', lambda: download_tucan_anmeldung(cred))

    module_ids = ( {module_id for courses in [courses, courses2, courses3, courses4]
                              for course in courses for module_id in course['modules']}
                 | inferno[regulations[0]].keys()
                 | inferno[regulations[1]].keys() )
    modules = json_read_or(prefix+'inferno-modules.json',
      lambda: download_from_inferno(cred, module_ids))
    modules = inner_join(courses, modules)
    for regulation in regulations:
        module_part = {k:v for k,v in modules.items() if regulation in str(v['regulations'])}
        short_regulation = "".join(c for c in regulation if c.isalnum())
        json_write(prefix+'-'+short_regulation+'.json', module_part)
    print()

################################################################################
# download

def download_inferno(credentials, roles):
    print("\ninferno", roles)
    browser = log_into_sso(credentials)
    # make new plan, with master computer science 2015, in german
    page = browser.get(INFERNO_URL + "/pp/plans?form&lang=de")
#    lst  = (set(page.soup.select(".planEntry label a"))
#          - set(page.soup.select(".planEntry label a.inactive")))
    form = page.soup.form
    option = [(i.text, i['value'])
              for i in form.select("#_regularity_id option")
              if i.text in roles]
    result = {}
    for k,v in option:
      urlopt = "?form=&regularity=" + v
      page = browser.get(INFERNO_URL + form['action'] + urlopt)
      # group entries hierarchically
      toplevel = page.soup.select_one("#plan div > ul li")
      result[k] = dict(flatten_inferno(toplevel, []))
    return result

def download_from_inferno(credentials, module_ids):
    print("\nfrom inferno" +" " + str(len(module_ids)))
    browser = log_into_sso(credentials)
    page = browser.get(INFERNO_URL)
    # download all entries
    status = {'ready':len(module_ids), 'finished':0}
    with mp.Pool(POOLSIZE) as p:
        return list(p.map(lambda x: get_inferno_page(browser, status, x), module_ids))

def download_tucan_vv_catalogue(credentials, FBs):
    print("\ntucan-vv catalogue FB20")
#    limit = json_read("nebenfach.json")
#    limit = set(key for fach in limit.values()
#                    for cat in fach.values()
#                    for fach in cat
#                    for key in fach)
    (browser, page) = log_into_tucan(credentials)
    page = browser.get(TUCAN_URL + page.soup.select_one('li[title="VV"] a')['href'])
    result = []
    for FB in FBs:
        link = [i for i in page.soup.select("#pageContent a") if i.text.startswith(" FB"+FB)][0]
        data = walk_tucan(browser, TUCAN_URL + link["href"]) #, limit=None if FB=="20" else limit)
        result.extend(data)
    return result

def download_tucan_vv_search(credentials):
    print("\ntucan-vv search")
    (browser, page) = log_into_tucan(credentials)
    page = browser.get(TUCAN_URL + page.soup.select_one('li[title="Lehrveranstaltungssuche"] a')['href'])
    form = ms.Form(page.soup.select_one("#findcourse"))
    semester_list = [(i.text, i['value']) for i in page.soup.select('#course_catalogue option')]
    print(semester_list[0])
    form['course_catalogue'] = semester_list[0][1] # neustes semester
    form['with_logo'] = '2' # we need two criteria to start search, this should show everything
    form.choose_submit("submit_search")
    page = browser.submit(form, TUCAN_URL + form.form['action'])
    return walk_tucan_list(browser, page)

def download_tucan_anmeldung(credentials):
    print("\ntucan anmeldung david")
    (browser, page) = log_into_tucan(credentials)
    link = page.soup.select_one('li[title="Anmeldung"] a')['href']
    data = walk_tucan(browser, TUCAN_URL + link)
    return data

def download_tucan_vv_pages(credentials, courses):
    print("\ntucan-vv each page")
    (browser, page) = log_into_tucan(credentials)
    session_key = page.url.split("-")[2][:-1]
    i, maxi = [0], len(courses)
    with mp.Pool(POOLSIZE) as p:
        return p.map(lambda title_url: get_tucan_page(browser, title_url, session_key, i, maxi), courses)

def inner_join(courses, modules):
    modules = {item['module_id']:item for item in modules} # for module_id in item['modules']}
    courses = ((module_id, item) for item in courses for module_id in item['modules']
                                 if module_id in modules)
    return {k:merge(g, modules[k]) for k,g in groupby(courses, key=lambda x:x[0])}

def merge(courses, module):
    courses = [i[1] for i in courses]

    # credits
    details = module['details']
    credits = 0
    credits_ = [i for i in details if i['title'] in ["Credit Points", "CP", "Credits"]]
    if len(credits_) > 0:
        try:
            credits = int(credits_[0]["details"].split(",")[0])
            details = [i for i in details if not i['title'] in ["Credit Points", "CP", "Credits"]]
        except:
            pass

    content = [{k:v for k,v in i.items() if k!="modules"} for i in courses]
    return merge_dict(module, {'content':content, 'details':details, 'credits':credits})

def flatten_inferno(item, path):
    path = path + [item.h2.text.replace("\t", "").replace("\n", "")]
    for item in list(item.find("ul", recursive=False).children):
        for i in flatten_inferno(item.li, path): yield i
        #yield from flatten_inferno(item.li, path)
    if item.find(class_="selectableCatalogue", recursive=False):
        catalogue = item.find(class_="selectableCatalogue", recursive=False)
        for item in catalogue.select(".planEntry label a"):
            if 'inactive' in item['class']: continue
            yield (item.text[:10], (path[-1], item.text.split(" - ")[1])) # last path part should be enough

################################################################################
# browser

INFERNO_PREFIX = "http://inferno.dekanat.informatik.tu-darmstadt.de/pp/plans/modules/"
def get_inferno_page(browser, status, module_id):
    status['finished'] += 1; progress(status['finished'], status['ready']) # progress
    page = browser.get(INFERNO_PREFIX + module_id + "?lang=de")
    details = extract_inferno_module(page.soup)
    # TODO get title
    try:
      regulations = [i['details']
                     for i in details['details']
                     if i['title'] == "Studiengangsordnungen"][0]
      return merge_dict(details, {'module_id':module_id, 'regulations':regulations})
    except:
      return merge_dict(details, {'module_id':module_id, 'regulations':[]})

def get_tucan_page(browser, title_url, session_key, i, maxi):
    i[0] += 1; progress(i[0], maxi)
    title, url = title_url
    url = url[:68] + session_key + url[84:]
    page = browser.get(TUCAN_URL + url)
    dates   = extract_tucan_dates(page.soup, blame=title)
    details = extract_tucan_details(page.soup, blame=title)
    modules = extract_tucan_course_modules(page.soup, blame=title)
    return merge_dict(details, {'title':title, 'dates':dates, 'modules':modules}) # 'link':url,

def walk_tucan_list(browser, page):
    limit = int(page.soup.select("#searchCourseListPageNavi a")[-1]['class'][0].split("_", 1)[1])
    result = []
    for i in range(2, limit):
        progress(i, limit)
        nav = page.soup.select_one("#searchCourseListPageNavi .pageNaviLink_"+str(i))
        result.extend( (i.text, i['href']) for i in page.soup.select("a[name='eventLink']") )
        page = browser.get(TUCAN_URL + nav['href'])
    result.extend( (i.text, i['href']) for i in page.soup.select("a[name='eventLink']") )
    return result

def walk_tucan(browser, start_page, limit=None):
    with ParallelCrawler(POOLSIZE) as p:
        def walk_tucan_(link, linki):
            page = browser.get(link)
            title = linki['title']
            path = linki['path'] + [title]
            print("\r" + "  "*len(linki['path']) + " > " + title)
            progress(p._finished, p._ready, 300)
            if isParent(link):
                for nlink, nlinki in extract_links(page.soup, path):
                    if (limit is None
                    or isCourse(nlink) == (nlinki['title'][:10] in limit)):
                        p.apply(walk_tucan_, nlink, nlinki)
                return link, None
            elif isModule(link):
                return link, merge_dict(extract_tucan_details(page.soup, blame=title),
                  {'modules':[title[:10]], 'title':title}) # 'link':link
            elif isCourse(link):
                dates   = extract_tucan_dates(page.soup, blame=title)
                details = extract_tucan_details(page.soup, blame=title)
                modules = extract_tucan_course_modules(page.soup, blame=title)
                return link, merge_dict(details,
                  {'title':title, 'dates':dates, 'modules':modules}) # 'link':link,
        p.apply(walk_tucan_, start_page, dict(title='', path=[]))
        return [i for i in p.get().values() if i and 'title' in i]

################################################################################
# soup extractors

def parse_dates(dates):
    def get_time(day, start, end, room):
        return "\t".join([day.text[4:].strip(),
                          day.text[:2].strip(),
                          start.get_text(strip=True),
                          end.get_text(strip=True),
                          room.get_text(strip=True)])

    return [
        get_time(*event.find_all("td")[1:5])
        for event in dates.find_all("tr")[1:]
    ]

#    from datetime import datetime as dt
#    sorted_dates = sorted(dt.strptime(i[-1].replace(".", ""), "%d %b %Y") for i in events)
#    return list(sorted_dates)

#    first = last = first_to_last = ""
#    if len(sorted_dates) > 0:
#      first = sorted_dates[ 0].strftime("%Y-%m-%d")
#      last  = sorted_dates[-1].strftime("%Y-%m-%d")
#      first_to_last = "Termine liegen von %s bis %s:<br>" % (
#          sorted_dates[ 0].strftime("%d. %b"),
#          sorted_dates[-1].strftime("%d. %b"),
#      )
#    weekly = [{"count": v, "time": k,
#               "start": utils.fmt_hm(*k[1]), "end": utils.fmt_hm(*k[2]),
#               "room": k[3], "day_nr": k[0], "day": utils.num_to_day[k[0]]}
#              for k, v in collections.Counter(i[:-1] for i in events).items()
#              if v > 1]
#    weekly.sort(key=lambda a: (-a["count"], a["time"][0]))
    #return first_to_last, weekly, first, last

def extract_links(soup, path):
    def details(link): return TUCAN_URL + link['href'], {
        'title': link.text.strip(),
        'path': path
    }
    SELECTOR = '#pageContent ul li, #pageContent table tr'
    return [details(x.a) for x in soup.select(SELECTOR)
            if x.text.strip() not in BLACKLIST and x.a]

def extract_inferno_module(soup):
    SELECTOR = '#_title_ps_de_tud_informatik_dekanat_modulhandbuch_model_Module_id .fieldRow'
    return sanitize_details({"title":   str(i.find("label").text).strip(),
                             "details": str(i.find("div")).strip()}
                             for i in soup.select(SELECTOR))

def extract_tucan_details(soup, blame):
    try:
        details_raw = soup.select_one('#pageContent table:nth-of-type(1) .tbdata')
        return sanitize_details({"title":   x.split('</b>')[0].strip(),
                                 "details": x.split('</b>')[1].strip()}
                                 for x in str(details_raw).split('<b>')[1:])
    except Exception as e:
        print('\n(warn: no details for "{}" cause {})'.format(blame, e))
        return {}

def extract_tucan_course_modules(soup, blame):
    try:
        tables = soup.select('table.tb')
        table = get_table_with_caption(tables, 'Enthalten in Modulen')
        if not table: return []
        return [i.text.strip()[:10] for i in table.select("td")[1:]]
    except Exception as e:
        print('\n(warn: no modules for "{}" cause {})'.format(blame, e))
        return []

def extract_tucan_dates(soup, blame):
    try:
        tables = soup.select('table.tb')
        course_dates = get_table_with_caption(tables, 'Termine')
        if not course_dates: return
        #for link in course_dates.select('a'): link['href'] = ''
        if len(course_dates.select('tr')) > 2: return parse_dates(course_dates)
        return ""
    except Exception as e:
        print('\n(warn: no dates for "{}" cause {})'.format(blame, e))
        return ""

def get_table_with_caption(tables, caption):
    try: return [table for table in tables if table.caption and caption in table.caption.text][0]
    except IndexError: pass

#def get_links_of_table_with_caption(page, caption):
#    tables = page.select('table.tb')
#    table = get_table_with_caption(tables, caption)
#    if not table: return
#    return set(TUCAN_URL + x['href'] for x in table.select('tr a'))

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

def isParent(x): return "&PRGNAME=REGISTRATION"  in x or "&PRGNAME=ACTION" in x
def isCourse(x): return "&PRGNAME=COURSEDETAILS" in x
def isModule(x): return "&PRGNAME=MODULEDETAILS" in x

################################################################################
# abstract helper functionality

def progress(current, maximum, hintmaximum=None):
  # print a progress bar like [*****-----------]
  if hintmaximum is None: hintmaximum = maximum
  MAX = 80
  a = int(current/hintmaximum*MAX)
  b = int(maximum/hintmaximum*MAX)-a
  c = MAX-a-b
  sys.stderr.write("\r[" + "*"*a + "."*b + "]" + " "*c + " "
                  + str(current) + "/" + str(maximum) + " ")
  sys.stderr.flush()

def merge_dict(x, y):
    # return {**x, **y}
    z = x.copy()
    z.update(y)
    return z

def json_write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)

def json_read(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def json_read_or(path, func):
    result = json_read(path)
    if result: return result
    a = time.time()
    data = func()
    json_write(path, data)
    b = time.time()
    print("\n", "{:0.2f} min".format((b-a)/60))
    return data

#class mpPool():
#  def __init__(self, size):
#     self._pool = mp.Pool(size)
#  def map(self, f, l):
#    def myfunc(y):
#      try:
#        return f(y)
#      except Exception as e:
#        import traceback; traceback.print_exc()
#        raise e
#    return self._pool.map(myfunc, l)
#  def close(self): return self._pool.close()
#  def join(self): return self._pool.join()
#  def apply_async(func, args, callback, error_callback):
#     def myfunc(*a, **b):
#         try:
#           callback(func(*a, **b))
#         except Exception as e:
#           error_callback(e)
#     self._pool.apply_async(myfunc, args, callback=mycallback)
#     #result = self._pool.apply_async(func, args=args, callback=callback, error_callback=error_callback)
#  def __enter__(self):
#    return self
#  def __exit__(self, exc_type, exc_val, exc_tb):
#     self._pool.close()
#     self._pool.join()

class ParallelCrawler():
    __slots__ = ["_ready", "_finished", "_pool", "_event", "_result", "_lock"]
    def __init__(self, threads=None):
        self._pool = mp.Pool(POOLSIZE)
        self._event = mp.Event()
        self._result = dict()
        self._ready = 0
        self._finished = 0
        self._lock = mp.Lock()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._pool.close()
        self._pool.join()
    def apply(self, func, *args):
        """ func :: Key -> (Key, Value)

            func must take a single argument and return an key-value tuple,
            that is then inserted into a hashmap. (The returned key must be
            equal to the argument the function was called with.)

            Then you can call self.get() to wait for all results and return a
            dictionary that maps the keys to the values. """
        def error_cb(exc):
            print("")
            raise exc
        def cb(result):
            try:
                with self._lock:
                    self._result[result[0]] = result[1]
                    self._finished += 1
                    if self._ready == self._finished: self._event.set()
            except:
                print("")
                traceback.print_exc()
                self._event.set()
        with self._lock:
            if args[0] in self._result: return
            self._ready += 1
            self._result[args[0]] = None
        self._pool.apply_async(func, args, callback=cb, error_callback=error_cb)
    def get(self):
        self._event.wait()
        return self._result

def groupby(iterator, key):
    lst = sorted(iterator, key=key)
    return itertools.groupby(lst, key)

################################################################################
# helper

def get_credentials():
  return {"username": _get_config('TUID_USER'),
          "password": _get_config('TUID_PASS', is_password=True)}

def _get_config(variable, default=None, is_password=False):
    value = os.environ.get(variable, default)
    if value is None:
        if is_password:
            value = getpass.getpass(variable + ": ")
        else:
            sys.stderr.write(variable + ": ")
            sys.stderr.flush()
            value = input()
    return value

def _get_redirection_link(page):
    return TUCAN_URL + page.soup.select('a')[2].attrs['href']

def anonymous_tucan():
    browser = ms.Browser(soup_config={"features":"lxml"})
    page = browser.get(TUCAN_URL)
    page = browser.get(_get_redirection_link(page)) # HTML redirects, because why not
    page = browser.get(_get_redirection_link(page))
    return browser, page

def log_into_tucan(credentials):
    (browser, page) = anonymous_tucan()
    login_form = ms.Form(page.soup.select('#cn_loginForm')[0])
    login_form['usrname'] = credentials["username"]
    login_form['pass']    = credentials["password"]
    page = browser.submit(login_form, page.url)

    redirected_url = "=".join(page.headers['REFRESH'].split('=')[1:])
    page = browser.get(TUCAN_URL + redirected_url)
    page = browser.get(_get_redirection_link(page))
    return (browser, page)

def log_into_sso(credentials):
    browser = ms.Browser(soup_config={"features":"html.parser"})
    page = browser.get(SSO_URL)
    message = page.soup.select("#msg")
    if message and not 'class="success"' in str(message): raise Exception(message[0])

    form = ms.Form(page.soup.select('#fm1')[0])
    form["username"] = credentials["username"]
    form["password"] = credentials["password"]
    page = browser.submit(form, page.url)

    message = page.soup.select("#msg")
    if message and not 'class="success"' in str(message): raise Exception(message[0])
    return browser

################################################################################
# main

if __name__ == '__main__':
    main()

