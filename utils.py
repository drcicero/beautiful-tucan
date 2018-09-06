import json, re, collections, datetime, os.path, time, itertools

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

