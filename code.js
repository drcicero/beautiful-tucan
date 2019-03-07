// detect localStorage
try {
  localStorage.setItem('test', 'test');
  localStorage.removeItem('test');
  window.hasLocalStorage = true;
} catch(e) {
  window.hasLocalStorage = false;
}

//search_input.onchange = function () {}

// defs
var $  = x => Array.from(document.querySelectorAll(x));
var $$ = x => document.querySelector(x);
var noCommonElement = (x,y) => x.filter(e => y.includes(e)).length == 0;
var delClass = c => e => e.classList.remove(c);
var addClass = c => e => e.classList.add(c);
//var copy = it => JSON.parse(JSON.stringify(it));

var colors = [0,1,2,3,4,5,6,7,8,9,10,11,];

// do grid[t].push(id) for min_t<t<max_t where a number 'id' that is not yet
// inside any grid[t]; and return the id.
function allocate(grid, min_t, max_t) {
  var id = find_id(grid, min_t, max_t);
  for (var t=min_t; t<max_t; t++) {
    if (!(t in grid)) grid[t] = [];
    grid[t].push(id)
  }
  return id;
}

function find_id(grid, min_t, max_t) {
  for (var id=0; id<20; id++) {
    var ok = true;
    for (var t=min_t; t<max_t; t++)
      ok = ok && (grid[t]||[]).indexOf(id)===-1;
    if (ok) break;
  }
  return id;
}

function uniq(lst) {
  var last;
  return lst.filter(i => { var ok = i != last; last = i; return ok; })
}

function num_to_day(x) { return ["Mo","Di","Mi","Do","Fr","Sa","So"][x]; }
var format_timespan = w => ""
  + (""+w.start[0]).padStart(2,'0') + ":"
  + (""+w.start[1]).padStart(2,'0')
  + " - "
  + (""+w.end[0]).padStart(2,'0') + ":"
  + (""+w.end[1]).padStart(2,'0');
var format_weekly = w => num_to_day(w.day) + " " + format_timespan(w);

// use localStorage
function saveState() {
  if (hasLocalStorage) {
    localStorage.checked = JSON.stringify($("input").map(x => [x.id, x.checked]));
    localStorage.uebungs = JSON.stringify(window.selectuebungs);
  }

  var selected = $("input.checker")
    .filter(elem => elem.checked)
    .map   (elem => course_by_id[elem.id.substring(elem.id.indexOf("-")+1)]);

  var uebungs = {};
  selected.map(course => course.weekly.filter(w => w.room === "Übung").forEach(w =>
    (uebungs[course.id] || (uebungs[course.id]=[])).push(w.day + format_weekly(w))
  ));
  Object.values(uebungs).forEach(x => x.sort());

  var termine = "";
  if (selected.length > 0) {
    var first = new Date(selected
      .map   (course => +new Date(course.first))
      .filter(x      => x)
      .reduce((x,y)  => Math.min(x, y)));

    var last = new Date(selected
      .map   (course => +new Date(course.last))
      .filter(x      => x)
      .reduce((x,y)  => Math.max(x, y)));

    var mkRow = lst => "<tr><td>" + lst.join("</td><td>") + "</tr></td>"

    var selectedweekly = selected
      //.filter(x => x.weekly.length>0)
      .map(x => x.weekly
          .filter(w => w.room !== "Übung" || selectuebungs[x.id] === format_weekly(w))
          .map(y => y.day + mkRow([
              y.count + "x", num_to_day(y.day),
              format_timespan(y), x.title_short, "(" + y.room + ")"
          ]))
      ).reduce((x,y) => x.concat(y))
      .sort()
      .map( x => x.substring(1) );

    termine = (""
      + "(Termine liegen zwischen "
      + first.getDate() +"."+ (first.getMonth()+1) +"."+ first.getFullYear()
      + " und "
      + last.getDate() +"."+ (last.getMonth()+1) +"."+ last.getFullYear()
      + "):<br/><table>" //+ mkRow(["", "Tag", "Zeit", "Kurs", "Raum"])
      + selectedweekly.join("")
      + "</table><br/>"
    );
  }

  var events = pre_events.filter(w =>
    selected.some(y => y.id == w.id) &&
    (w.room !== "Übung" || selectuebungs[w.id] === format_weekly(w)));
  var assoc = new Map();
  var grid = {};
  events.forEach(w =>
    assoc.set(w.id + format_weekly(w), allocate(grid, w.starti, w.endi))
  );
  var found = {size:Math.max.apply(Math, [0, ...(grid[0]||[])])};
  var subblock = [found];
  for (var t=1; t<times.length; t++) {
    if (noCommonElement(grid[t]||[], grid[t-1]||[])) found = {size:0};
    if (grid[t]) found.size = Math.max.apply(Math, [found.size, ...grid[t]]);
    subblock[t] = found;
  }

//  var box = main2.getClientRects()[0];
  var width  = 100;
  var height = 480;

  main2.innerHTML = (""
//    + "Für Regelstudienzeit sind durchschnittlich jedes Semester 30 CP vorgesehen.<br>"
    + "Du hast "
    + selected
      .map   (course => parseInt(course.credits))
      .reduce((x,y) => x+y, 0)
    +" CP in folgenden Kursen ausgewählt:<br>"
    + selected.map(course => course.title_short + " (" + parseInt(course.credits) + "cp)").join(", ")
    + "<br><br>"

    + (Object.keys(uebungs).length === 0 ? "" :
        "Kleingruppen wählen:<br>"
      + Object.entries(uebungs).map(kv =>
        course_by_id[kv[0]].title_short
        + ": <select data-courseid='"+kv[0]+"'><option>Kleingruppentermin wählen</option>"
        + kv[1].map(v => "<option"+(selectuebungs[kv[0]] === v.substr(1)?" selected":"")+">"+v.substr(1)+"</option>").join("") + "</select>"
      ).join("<br>")
      + "<br><br>"
    )

    + "Wochen-Kalender:"
    + "<table style=width:100%>"
      + "<td style=width:20%>Mo</td>"
      + "<td style=width:20%>Di</td>"
      + "<td style=width:20%>Mi</td>"
      + "<td style=width:20%>Do</td>"
      + "<td style=width:20%>Fr</td>"
    + "</table>"

    + "<div style='position:relative;background:#eee;width:"+width+"%;height:"+height+"px;font-size:0.8em'>"
    + [0,1,2,3,4].map( d=> [...Array(7).keys()].map( h =>
        "<div class=box-c style="+
        "'width:"+(width/5-2)+"%;top:"+(h*73.33)+"px;left:"+(d*width/5)+"%'></div>"
      ).join("")).join("\n")

    + selected.map( select => select.weekly.map( week => {
      var gotassoc = assoc.get(select.id + format_weekly(week));
      if (gotassoc === undefined) return "";
      var parallelBlocks = subblock[
        times.indexOf(week.day*24*60 + week.start[0]*60 + week.start[1])
      ].size+1;
      var lshift = width/5/parallelBlocks * gotassoc;
      var left   = width/5      * week.day + lshift;
      var top    = height/12/60*10 * ((week.start[0]-8) * 60 + week.start[1])/ 10;
      var h      = height/12/60*10 * ((week.end[0]-8) * 60 + week.end[1])/ 10 - top;
      var w      = width/5/parallelBlocks - 2;
      var desc = select.title_short + " - " + format_timespan(week) + "<br>"
               + week.room + "<br>findet " + week.count + " Mal statt"
             /*+ select.first.substr(8,2) +"."+ select.first.substr(5,2)*/;
      var class_ = " class='box-b box-b-" + select.id + " color-" + (data.indexOf(select)%colors.length) + "'";
      var title  = " title='" + desc.replace(/<br>/g, "\n") + "\n" + select.title + "'";
      var style  = " style='position:absolute;top:"+top+"px;left:"+left+"%;width:"+w+"%;height:"+h+"px'";
      return "<div" + class_ + title + style + ">" + desc + "</div>";
    } ).join("\n")).join("\n")
    + "</div><br>"
  
    + termine
    + selected.map(x => x.title_short +": "+ x.title).join("<br/>")
  );

  $("select").forEach(x => x.onchange = e => {
    selectuebungs[e.target.dataset.courseid] = e.target.value;
    saveState();
    $("select").filter(x => x.dataset.courseid === e.target.dataset.courseid)[0].focus();
  });

  $(".box-b").forEach(x => x.onmouseenter = () =>
    $("."+Array.from(x.classList).filter(c=>c.startsWith("box-b-"))[0])
      .forEach(addClass("highlight-box-b")));
  $(".box-b").forEach(x => x.onmouseleave = () =>
    $(".highlight-box-b")
      .forEach(delClass("highlight-box-b")));

  $(".box-b:not(summary)").forEach(x => x.onclick = ()=> {
    var boxbid = Array.from(x.classList).filter(x => x.startsWith('box-b-'))[0]
    $("summary." + boxbid)[0].scrollIntoView();
  });

  // deselect all unselectable
  $(".conflicting").forEach(delClass("conflicting"));
  pre_events.filter(x => x.room !== "Übung").forEach(entry => {
    var id = find_id(grid, entry.starti, entry.endi);
    var obj = $$("summary.box-b-"+entry.id).classList;
    if (id !== 0) obj.add("conflicting");
  });
};

// create div from course
window.lastSuperCategory = null;
window.lastCategory = null;
function courseDiv(course) {
  var result = (
    "<span>" + course.credits + "CP</span>"
  + "<span>" + course.title_short + "</span>"
  + "<span title='"
     + course.title + "'>" + course.title + "</span>"
  + "<span title='"
     + course.owner + "'>" + course.owner_short + "</span>"
  );

  var checker = '<label><input class=checker type="checkbox" id="checker-' + course.id + '"/></label>'

  var cat = course.category.replace(' ', '-');
  var category = (lastCategory == course.category ? "" :
      '<br/></details><details class=category open>'
    + '<summary><div class=toggler-show></div>'
    + '<b>' + course.category + '</b><clear/></summary>'
  );
  window.lastCategory = course.category;

//  var cat = course.category.replace(' ', '-');
//  var category_start_html = ('<div class=category>'
//    + '<input class=toggler type="checkbox" id="toggler-' + cat + '"/>'
//    + '<label class=toggler for="toggler-' + cat + '"><div class=toggler-show></div>'
//    + '<b>' + (course.category[0]=="Y" ? course.category.slice(14) : course.category) + '</b><clear/></label>');

//  var category = (lastSuperCategory == (course.category[0]=="Y") ? (lastCategory == course.category ? "" :
//      '<br/></div>' + category_start_html
//  ) :
//      '<br/></div></div><div class=category>'
//    + '<input class=toggler type="checkbox" id="toggler-' + (course.category[0]=="Y") + '"/>'
//    + '<label class=toggler for="toggler-' + (course.category[0]=="Y") + '"><div class=toggler-show></div>'
//    + '<b>' + course.category[0] + '</b><clear/></label>' + category_start_html );
//  window.lastSuperCategory = course.category[0]=="Y";
//  window.lastCategory = course.category;

  var details = ""; // "<div class=esc>X</div><div class=prev>&lt;</div><div class=next>&gt;</div>";
  if (course.weekly && course.weekly.length > 0)
    details += "<b>" + course.first_to_last + "</b>"
      + course.weekly.map( x =>
          "* " + x.count +"x "+ format_weekly(x) +" ("+ x.room +")"
        ).join("<br/>")
      + "<br/><br/>";
  details += "<b>Kurse</b><br/>" + uniq(course.content.map(x=>x.title)).join("<br/>\n")+"<br/><br/>"
  details += course.details.filter(x=>x.details != "").map( x =>
    "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n");
  details += JSON.stringify(course.uedates);

  return category + ( "<div class=flex>"
    + checker
    + "<details class=course-wrapper style=''>"
      + "<summary id='course-" + course.id + "' class='course box-b box-b-" + course.id + "'>"
        + result
        + "<div class=toggler-show></div>"
      + "</summary>"
      + "<div class=details id='details-" + course.id + "'>"
        + details
      + "</div>"
    + "</details></div>"
  );
}

window.onload = function() {

  window.selectuebungs = {};

  window.course_by_id = {};
  data.forEach(x => course_by_id[x.id]=x);

  window.pre_events = data
    .map   (x => x.weekly.map(y => ({
      id: x.id, title_short: x.title_short,
      count: y.count, day: y.day, start: y.start, end: y.end, room: y.room,
      starti: y.day * 24*60 + y.start[0] * 60 + y.start[1],
      endi:   y.day * 24*60 + y.end[0]   * 60 + y.end[1],
    })))
    .reduce((x,y)=>x.concat(y), [])
    .filter (x => x.count>1)
    .sort((x,y) => ((y.endi-y.starti) - (x.endi-x.starti))*(5*24*60) + x.starti-y.starti);
  window.times = pre_events
    .map   (event => [event.starti, event.endi])
    .reduce((x,y) => x.concat(y), []);
  window.times = [...new Set(times)];
  times.sort((x,y) => x-y);
  pre_events.forEach(event => {
    event.starti = times.indexOf(event.starti);
    event.endi   = times.indexOf(event.endi);
  });

  // show courses
  window.lastCategory = null;
  main.innerHTML = "<div><details hidden>" + data.map(courseDiv).join("\n") + "</details></div>";

  // load state
  if (hasLocalStorage) {
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) elem.checked = x[1];
      if (elem && elem.classList.length>0 && x[1]) elem.parentElement.nextSibling.classList.toggle(
        elem.classList[0].replace("er", "ed"));
    });
    window.selectuebungs = JSON.parse(localStorage.uebungs || "{}");
  }

  // enable toggles
  $("input.checker").forEach( x => x.onclick = e => {
    x.parentElement.nextSibling.classList.toggle("checked");
    saveState();
  });
  $(".course-wrapper > summary").forEach(x => x.onclick = () =>
    $(".course-wrapper > summary").forEach(y => x !== y ? y.parentElement.open = false : ""));

  var esc = () => {
    var courses = $(".course-wrapper > summary");
    courses[courses.findIndex(x => x.parentElement.open)].click();
  };
  var prev = () => {
    var courses = $(".course-wrapper > summary");
    courses[courses.findIndex(x => x.parentElement.open)-1].click();
  };
  var next = () => {
    var courses = $(".course-wrapper > summary");
    courses[courses.findIndex(x => x.parentElement.open)+1].click();
  };
  document.onkeyup = (e) => {
    if      (e.keyCode === 27) esc();
    else if (e.keyCode === 37) prev();
    else if (e.keyCode === 39) next();
  };

//  $(".esc") .forEach(but => but.onclick = esc))
//  $(".prev").forEach(but => but.onclick = prev);
//  $(".next").forEach(but => but.onclick = next);


//  remove_unchecked.onclick = ()=> {
//    $(".hidden").forEach(delClass("hidden"));
//    $("input.input")
//    .filter(x => !x.checked)
//    .forEach(x => {
//      x.parentElement.classList.add("hidden");
//      var y = document.getElementById("item2-" + x.id.substring(x.id.indexOf("-")))
//      if (y) y.classList.add("hidden");
//    });
//  };


//  show_all.onclick = function() {
//    $(".hidden").forEach(delClass("hidden"));
//  }

  saveState();
}
document.addEventListener("pjax:success", window.onload)

