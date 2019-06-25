import json, re, datetime, os.path, time, itertools, sys, getpass, traceback
import multiprocessing as mp

num_to_day = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
day_to_num = {day:i for i,day in enumerate(num_to_day)}


def half_semester(now):
  return ("Sommer "+ now.strftime("%Y") if 3 <= now.month < 9 else
          "Winter " + now.strftime("%Y") +"/"+ str(int(now.strftime("%Y")[2:])+1))
def half_semester_filename(now):
  return (now.strftime("%Y") if 3 <= now.month < 9 else
          now.strftime("%Y") +"-"+ str(int(now.strftime("%Y")[2:])+1))

def fmt_hm(h, m):
    return str(h).zfill(2) + ":" + str(m).zfill(2)

def parse_hm(h_m):
    h, m = h_m.split(":", 1)
    return int(h), int(m)

def sanitize_date(i):
  # translate germany -> english
  string = (i.replace(".", "")
    .replace("Mär", "Mar")
    .replace("Mai", "May")
    .replace("Okt", "Oct")
    .replace("Dez", "Dec"))
  return datetime.datetime.strptime(string, "%d %b %Y").strftime("%Y-%m-%d")

def roman_to_latin_numbers(title):
    return (title
            .replace(" I ", " 1 ")
            .replace(" II ", " 2 ")
            .replace(" III ", " 3 ")
            .replace(" IV ", " 4 ")
            .replace(" V ", " 5 ")
            )

def remove_bracketed_part(title):
    return " ".join(re.match("([^(]*)(?:[(][^)]*[)])?(.*)", title).groups())


#def from_stream(tuples):
#    """
#    Creates a nested dictionary structure, where the tuples are the path
#    into the structure, and the last tuple element is the value.
#    each tuple must have at least 2 components.
#    example: [(1,'a'), (1,'b'), (2,3,4,'c')] --> {1:['a','b'],2:{3:{4:'c'}}}
#    """
#    result = collections.OrderedDict()
#    for t in tuples:
#        thing = result
#        for k in t[:-2]:
#            if k not in thing: thing[k] = collections.OrderedDict()
#            thing = thing[k]
#        if len(t) >= 2 and t[-2] not in thing: thing[t[-2]] = []
#        thing[t[-2]].append(t[-1])
#    return result

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

def groupby(iterator, key):
    lst = sorted(iterator, key=key)
    return itertools.groupby(lst, key)


def blame(msg, func):
    try: return func()
    except Exception as e:
      print("\r(warn: {} cause {} in line {})".format(msg, e, sys.exc_info()[-1].tb_lineno))

def progress(current, maximum):
    # print a progress bar like [*****-----------]
    MAX = 80
    a = int(current/maximum*MAX)
    b = MAX-a
    sys.stderr.write("\r[" + "*"*a + "."*b + "] " + str(current) + "/" + str(maximum) + " ")
    sys.stderr.flush()

def progresspmap(pool, func, lst):
    """ a parallel map with a progressbar. """
    i, maxi, result = 0, len(lst), []
    for item in pool.imap_unordered(func, lst):
        result.append(item)
        i += 1; progress(i, maxi)
    return result

def parallelCrawl(pool, func, args, limit=300):
    """
    Imagine it works like this:

    parallelCrawl :: Func -> Arg -> Dict[Arg, Result]
    func          :: Arg -> (Result, List[Arg])
    args          :: Arg

    parallelCrawl takes a function and initial argument.
    The functions takes such arguments and returns a tuple of
    the actual result and a list of interesting further arguments.

    The parallel crawler will then call the function for all those arguments
    and in turn for the arguments those calls return, until no further
    arguments are returned.

    Meanwhile the parallel crawler will accumulate a dict
    mapping interesting arguments to their actual result and return that dict.

    The argument has to be hashable so it will remember previous calls and
    not call the function for the same argument twice.
    """

    result = dict()
    event  = mp.Event()
    lock   = mp.Lock()

    ready    = 0
    finished = 0

    def fork(args):
        nonlocal ready

        def error_cb(exc):
            nonlocal finished

            traceback.print_exc()
            with lock:
                finished += 1
                if ready == finished: event.set()
            raise exc

        def cb(res):
            nonlocal finished
            try:
                value, forks = res
                for newargs in forks: fork(newargs)

                result[args[0]] = value
                with lock: finished += 1
                progress(finished, limit or ready)
                with lock:
                    if ready == finished: event.set()

            except:
                print("")
                traceback.print_exc()
                print("continue on error")
                event.set()

        if args[0] in result: return
        with lock: ready += 1
        result[args[0]] = None
        pool.apply_async(func, args, callback=cb, error_callback=error_cb)

    fork(args)
    event.wait()
    return result

def get_config(variable, default=None, is_password=False):
    value = os.environ.get(variable, default)
    if value is not None: return value
    if is_password:       return getpass.getpass(variable + ": ")
    sys.stderr.write(variable + ": ")
    sys.stderr.flush()
    return input()

