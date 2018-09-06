#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import division
import os, re, sys, json, getpass, warnings, datetime, traceback
import multiprocessing.dummy as mp
import utils

import bs4                  # html parsing
import mechanicalsoup as ms # GET, POST, cookie requests

POOLSIZE = 16 #  8  -->  ~6min

SSO_URL     = "https://sso.tu-darmstadt.de"
TUCAN_URL   = "https://www.tucan.tu-darmstadt.de"
INFERNO_URL = "http://inferno.dekanat.informatik.tu-darmstadt.de"


warnings.simplefilter('ignore', UserWarning) # ignore bs4 warnings like:
# """UserWarning: "b'////////'" looks like a filename, not markup.
#    You should probably open this file and pass the filehandle into Beautiful Soup."""


def main():
    if not os.path.exists('cache'): os.mkdir("cache")

    prefix = "cache/" + utils.half_semester_filename(datetime.datetime.today()) + "-"
    cred = get_credentials()

    get_inferno   = lambda: download_inferno(cred, [])
    get_pre_tucan = lambda: download_tucan_vv_search(cred)
    get_tucan     = lambda: download_tucan_vv_pages(cred, courses)
    inferno = utils.json_read_or(prefix+'inferno.json',   get_inferno)
    courses = utils.json_read_or(prefix+'pre-tucan.json', get_pre_tucan)
    courses = utils.json_read_or(prefix+'tucan.json',     get_tucan)
    regulations = list(inferno.keys())

#    # three alternative ways to get list of courses:
#    courses2 = utils.json_read_or(prefix+'tucan-FBs.json', lambda: download_tucan_vv_catalogue(cred,
#      # ("01", "02", "03", "04", "05", "11", "13", "16", "18", "20",)))
#    courses3 = utils.json_read_or(prefix+'tucan-FB20.json', lambda: download_tucan_vv_catalogue(cred,
#      # ("20",)))
#    courses4 = utils.json_read_or(prefix+'tucan-anmeldung.json', lambda: download_tucan_anmeldung(cred))

    module_ids = ( {module_id for course in courses for module_id in course['modules']}
                 | {key for regulation in regulations for key in inferno[regulation].keys()} )
    get_inferno_modules = lambda: download_from_inferno(cred, module_ids)
    modules = utils.json_read_or(prefix+'inferno-modules.json', get_inferno_modules)
    modules = inner_join(courses, modules)
    for regulation in regulations:
        module_part = {k:v for k,v in modules.items() if regulation in str(v['regulations'])}
        short_regulation = "".join(c for c in regulation if c.isalnum())
        utils.json_write(prefix+'-'+short_regulation+'.json', module_part)
    print()

################################################################################
# download

def download_inferno(credentials, roles):
    print("\ninferno")
    browser = log_into_sso(credentials)
    # make new plan, with master computer science 2015, in german
    page = browser.get(INFERNO_URL + "/pp/plans?form&lang=de")
#    lst  = (set(page.soup.select(".planEntry label a"))
#          - set(page.soup.select(".planEntry label a.inactive")))
    form = page.soup.form
    options = [(i.text, i['value'])
               for i in form.select("#_regularity_id option")]
    #print("options", options)
    result = {}
    for k,v in options:
      print("  * ", k)
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
    status = {'ready':len(module_ids), 'finished':0, 'printed':0}
    with mp.Pool(POOLSIZE) as p:
        return p.map(lambda x: get_inferno_page(browser, status, x), module_ids)

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

def walk_tucan_list(browser, page):
    limit = int(page.soup.select("#searchCourseListPageNavi a")[-1]['class'][0].split("_", 1)[1])
    result = []
    with ParallelCrawler(POOLSIZE, limit=limit) as p:
        def walk(href):
            page = browser.get(TUCAN_URL + href)
            navs = page.soup.select("#searchCourseListPageNavi a")
            for nav in navs: p.apply(walk, nav['href'])
            return href, [(i.text, i['href']) for i in page.soup.select("a[name='eventLink']")]
        p.apply(walk, page.soup.select_one("#searchCourseListPageNavi .pageNaviLink_1")['href'])
        return list(sorted(i for lst in p.get().values() for i in lst))

def download_tucan_vv_pages(credentials, courses):
    print("\ntucan-vv each page")
    (browser, page) = log_into_tucan(credentials)
    session_key = page.url.split("-")[2][:-1]
    i, maxi = [0], len(courses)
    with mp.Pool(POOLSIZE) as p:
        return p.map(lambda title_url:
            get_tucan_page(browser, title_url, session_key, i, maxi), courses)

def inner_join(courses, modules):
    modules = {item['module_id']:item for item in modules} # for module_id in item['modules']}
    courses = ((module_id, item) for item in courses for module_id in item['modules']
                                 if module_id in modules)
    return {k:merge(g, modules[k]) for k,g in utils.groupby(courses, key=lambda x:x[0])}

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
    details = extract_inferno_module(page.soup) or {}
    # TODO get title
    regulations = [i['details']
                   for i in details['details']
                   if i['title'] == "Studiengangsordnungen"]
    regulations = regulations[0] if regulations else []
    return utils.merge_dict(details, {'module_id':module_id, 'regulations':regulations})

def get_tucan_page(browser, title_url, session_key, i, maxi):
    i[0] += 1; progress(i[0], maxi)
    title, url = title_url
    url = url[:68] + session_key + url[84:]
    page = browser.get(TUCAN_URL + url)
    dates   = blame("no dates for '"+title+"'",   lambda: extract_tucan_dates(page.soup)) or []
    uedates = blame("no uedates for '"+title+"'", lambda: extract_tucan_uedates(page.soup, title)) or []
    details = blame("no details for '"+title+"'", lambda: extract_tucan_details(page.soup)) or {}
    modules = blame("no modules for '"+title+"'", lambda: extract_tucan_course_modules(page.soup)) or []
    return utils.merge_dict(details, {'title':title, 'dates':dates, 'uedates':uedates, 'modules':modules}) # 'link':url,

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
    return utils.merge_dict(module, {'content':content, 'details':details, 'credits':credits})

################################################################################
# soup extractors

def parse_uedate(string, blamei):
    # 'Fr, 16. Okt 2018 [13:30]-Fr, 16. Okt 2018 [13:30]' -> (day, start_hm, end_hm)
    start,  end    = string.split("-")
    s_wday, e_wday = start[:2],    end[:2]
    s_day,  e_day  = start[4:-8],  end[4:-8]
    s_hm,   e_hm   = start[-6:-1], end[-6:-1]
    if s_wday != e_wday: print("\r(warn: inequal start/end weekday for '{}' cause {} - {}"
      .format(blamei, start, end))
    return "\t".join([utils.sanitize_date(s_day), s_hm, e_hm])

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

def blame(msg, func):
    try: return func()
    except Exception as e:
      print("\r(warn: {} cause {} in line {})".format(msg, e, sys.exc_info()[-1].tb_lineno))

def extract_tucan_details(soup):
    details_raw = soup.select_one('#pageContent table:nth-of-type(1) .tbdata')
    return sanitize_details({"title":   x.split('</b>')[0].strip(),
                             "details": x.split('</b>')[1].strip()}
                             for x in str(details_raw).split('<b>')[1:])

def extract_tucan_course_modules(soup):
    tables = soup.select('table.tb')
    table = get_table_with_caption(tables, 'Enthalten in Modulen')
    if not table: return
    return [i.text.strip()[:10] for i in table.select("td")[1:]]

def extract_tucan_dates(soup):
    tables = soup.select('table.tb')
    course_dates = get_table_with_caption(tables, 'Termine')
    if not course_dates or len(course_dates.select('tr')) <= 2: return
    return parse_dates(course_dates)

def extract_tucan_uedates(soup, blamei):
    tables = soup.select('div.tb')
    if not tables: return
    course_dates = [t for t in tables if "Kleingruppe(n)" in t.select(".tbhead")[0].text]
    if not course_dates: return
    course_dates = course_dates[0]
    if not len(course_dates.select('li')): return
    return [parse_uedate(i.select('p')[2].text, blamei)+"\t"+i.strong.text.strip()
            for i in course_dates.select('li') if i.select('p')[2].text.strip() != ""]

def get_table_with_caption(tables, caption):
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
# abstract helper functionality

def progress(current, maximum):
  # print a progress bar like [*****-----------]
  MAX = 80
  a = int(current/maximum*MAX)
  b = MAX-a
  sys.stderr.write("\r[" + "*"*a + "."*b + "] " + str(current) + "/" + str(maximum) + " ")
  sys.stderr.flush()

class ParallelCrawler():
    __slots__ = ["_ready", "_finished", "_limit", "_pool", "_event", "_result", "_lock"]
    def __init__(self, threads=None, limit=300):
        self._pool = mp.Pool(POOLSIZE)
        self._event = mp.Event()
        self._result = dict()
        self._lock = mp.Lock()

        self._ready = 0
        self._finished = 0
        self._limit = limit
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
            progress(self._finished, self._limit or self._ready)
        self._pool.apply_async(func, args, callback=cb, error_callback=error_cb)
    def get(self):
        self._event.wait()
        return self._result

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

    if not 'refresh' in page.headers: print(page.soup)
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

