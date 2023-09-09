// requires the function generateIcsDownload() to be defined

// flatMap polyfill
if (!Array.prototype.flatMap) {
  Object.defineProperties(Array.prototype, {
    flatMap: {
      configurable: true,
      value: function flatMap(callback) {
        return Array.prototype.map.apply(this, arguments)
          .reduce((x,y) => x.concat(y), []);
      },
      writable: true
    }
  });
}

// show error messages on mobile browsers
window.onerror = function (message, url, lineNo){
  var p = document.createElement("p")
  p.textContent = 'Error: ' + message + '\n' + 'Line Number: ' + lineNo;
  document.body.appendChild(p);
  return false; // do not swallow error in console
}

function genDownloadLink(text, filename, linktext) {
  // download file via <a href=data:... download=filename />
  var element = document.createElement('a');
  element.href = "data:text/calendar;charset=utf-8," + encodeURIComponent(text);
  element.download = filename;
  element.textContent = linktext;
  return element;
}

// defs
var $  = x => Array.from(document.querySelectorAll(x));
var $$ = x => document.querySelector(x);
var noCommonElement = (x,y) => x.filter(e => y.includes(e)).length == 0;
var delClass = c => e => e.classList.remove(c);
var addClass = c => e => e.classList.add(c);
var colors = 12;

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
  for (var id=0; id<20; id++) { // actually Max.Int not 20
    var ok = true;
    for (var t=min_t; t<max_t; t++)
      ok = ok && (grid[t]||[]).indexOf(id)===-1;
    if (ok) break;
  }
  return id;
}

function first_to_last(dates) {
  var first = new Date(dates
    .map    (x => +new Date(x))
    .filter (x => x)
    .reduce((x,y) => Math.min(x, y)));

  var last = new Date(dates
    .map   (x => +new Date(x))
    .filter(x => x)
    .reduce((x,y) => Math.max(x, y)));

  return ""
    + first.getDate() +"."+ (first.getMonth()+1) +"."+ first.getFullYear()
    + " und "
    + last.getDate() +"."+ (last.getMonth()+1) +"."+ last.getFullYear();
}

function num_to_day(x) { return ["Mo","Di","Mi","Do","Fr","Sa","So"][x]; }
var format_timespan = w => ""
  + (""+w.start[0]).padStart(2,'0') + ":"
  + (""+w.start[1]).padStart(2,'0')
  + " - "
  + (""+w.end[0]).padStart(2,'0') + ":"
  + (""+w.end[1]).padStart(2,'0');
var format_weekly = w => num_to_day(w.day) + " " + format_timespan(w);

function saveState() {
  location.hash = $("input").filter(x => x.checked).map(x => x.id.slice(8))
                + ";"+ btoa(JSON.stringify(selectuebungs));

  // checked modules
  var selected = $("input.checker")
    .filter(elem => elem.checked)
    .map   (elem => module_by_id[elem.id.substring(elem.id.indexOf("-")+1)]);

  // selectable uebungs combo-box
  var possibleUebungs = selected.map(module =>
    [module.id, module.weekly
      .filter(w => w.room.startsWith("Übung "))
      .map(w => w.day + format_weekly(w))
      .sort()]
  ).filter(kv => kv[1].length > 0);

  var termine = "";
  if (selected.length > 0) {
    var mkRow = lst => "<tr><td>" + lst.join("</td><td>") + "</tr></td>"
    var dates = selected
      .flatMap(module => Object.values(module.content))
      .flatMap(course => [...course.dates, ...course.uedates])
      .map(x => x.split("\t")[0]);

    var selectedonce = selected
      .flatMap(x => x.weekly
          .filter(w => !w.room.startsWith("Übung ") || selectuebungs[x.id] === format_weekly(w))
          .filter(w => w.count == 1)
          .map(y => [y.firstdate+format_timespan(y), mkRow([
              y.firstdate, num_to_day(y.day),
              format_timespan(y), x.title_short, "(" + y.room + ")"
          ])])
      )
      .sort()
      .map(x => x[1])
      .join("");

    var selectedweekly = selected
      .flatMap(x => x.weekly
          .filter(w => !w.room.startsWith("Übung ") || selectuebungs[x.id] === format_weekly(w))
          .filter(w => w.count != 1)
          .map(y => [y.day+format_timespan(y), mkRow([
              y.count + "x", num_to_day(y.day),
              format_timespan(y), x.title_short, "(" + y.room + ")"
          ])])
      )
      .sort()
      .map(x => x[1])
      .join("");

//...x[1].uedates.filter(
//        w => selectuebungs[x[0].id] ===
//               num_to_day(new Date(w.split("\t")[0]).getDay())
//               + " " + w.split("\t")[1]+" - "+w.split("\t")[2]
//      )

    termine = (""
      + genDownloadLink(generateIcsDownload(selected),
                        "beautiful-tucan.ics",
                        "Ausgewählte Termine downloaden (.ics), zb für Thunderbird/Lightning Calendar").outerHTML
      + "<br/>"
      + "<br/>"
      + "Einzel-Termine:<br/><table>"
      + selectedonce
      + "</table><br/>"
      + "Wiederholende Termine (zwischen "+ first_to_last(dates) +"):<br/><table>" // + mkRow(["", "Tag", "Zeit", "Kurs", "Raum"])
      + selectedweekly
      + "</table><br/>"
    );
  }

  var events = pre_events.filter(w =>
    selected.some(y => y.id == w.id) &&
    (!w.room.startsWith("Übung ") || selectuebungs[w.id] === format_weekly(w)));
  // allocate events into grid, get id
  var assoc = new Map();
  var grid = {};
  events.forEach(w => {
    var allocatedId = allocate(grid, w.starti, w.endi);
    assoc.set(w.id + format_weekly(w), allocatedId);
  });

  // divide week into timeranges of non-overlapping events,
  // count distinct events per such timerange
  var found = {size: Math.max.apply(Math, [0, ...(grid[0]||[])])};
  var subblock = [found];
  for (var t=1; t<times.length; t++) {
    // if one block and the next have no common element, then reset size to zero
    if (noCommonElement(grid[t]||[], grid[t-1]||[])) found = {size:0};
    // add distinct elements to size
    if (grid[t]) found.size = Math.max.apply(Math, [found.size, ...grid[t]]);
    subblock[t] = found;
  }

//  var box = main2.getClientRects()[0];
  var width       = 100;
  var height      = 480;
  var daywidth    = width  / 5;
  var hourheight  = height / 12;

  main2.innerHTML = (""
    + "<div id=main21>"
    + "Du hast "
    + selected
      .map   (module => parseInt(module.credits))
      .reduce((x,y) => x+y, 0)
    +" CP in folgenden Kursen ausgewählt:<br>"
    + selected.map(module => module.title_short + " (" + parseInt(module.credits) + "cp)").join(", ")
    + "<br><br>"
    + "</div>"

    + "<div id=main22>"
    + (possibleUebungs.length === 0 ? "" :
        "Kleingruppen wählen:<br>"
      + possibleUebungs.map(kv =>
        "<select data-moduleid='"+kv[0]+"'><option>Kleingruppentermin wählen</option>"
        + kv[1].map(v => "<option"+(selectuebungs[kv[0]] === v.substr(1)?" selected":"")+">"+v.substr(1)+"</option>").join("") + "</select>"
        + module_by_id[kv[0]].title_short
      ).join("<br>")
      + "<br><br>"
    )
    + "</div>"

    + "<div id=main23>"
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
        "'width:"+(daywidth-2)+"%;top:"+(h*73.33)+"px;left:"+(d*daywidth)+"%'></div>"
      ).join("")).join("\n")

    + selected.map( select => select.weekly.filter(x=>x.count>1).map( week => {
      var part = assoc.get(select.id + format_weekly(week));
      if (part === undefined) return "";

      var timesidx = week.day*24*60 + week.start[0]*60 + week.start[1];
      var parts    = subblock[times.indexOf(timesidx)].size+1;

      var left = daywidth * week.day + part/parts * daywidth;
      var top  = hourheight * ((week.start[0]-8) + week.start[1]/60);
      var bot  = hourheight * ((week.end  [0]-8) + week.end  [1]/60);
      var h    = bot - top;
      var w    = daywidth/parts - 1;

      var dates = Object.values(select.content)
        .flatMap(course => [...course.dates, ...course.uedates])
        .map(x => x.split("\t")[0]);

      var desc  = select.title_short + " - " + format_timespan(week) + "<br>"
                + week.count +"x in "+ week.room;
      var ldesc = select.title + "\n"
                + format_timespan(week) + "\n"
                + week.room + "\n"
                + "findet " + week.count + " Mal statt\n"
                + "zwischen " + first_to_last(dates);

      var c1 = "box-b ";
      var c2 = "box-b-" + select.id + " ";
      var c3 = "color-" + (data.indexOf(select)%colors) + " ";

      var s1 = "position:absolute;";
      var s2 = "top:" + top + "px;";
      var s3 = "left:" + left + "%;";
      var s4 = "width:" + w + "%;";
      var s5 = "height:" + h + "px;";

      var a1 = "class='" + c1 + c2 + c3 + "' ";
      var a2 = "style='" + s1 + s2 + s3 + s4 + s5 + "' ";
      var a3 = "title='" + ldesc + "' ";

      return "<div " + a1 + a2 + a3 + ">" + desc + "</div>";
    } ).join("\n")).join("\n")
    + "</div>"
    + "</div>"
    + "<br/>"

    + "<div id=main24>" + termine + "</div>"
    + "<div id=main25>" + selected.map(x => x.title_short +": "+ x.title).join("<br/>") + "</div>"
  );

  $("select").forEach(x => x.onchange = e => {
    selectuebungs[e.target.dataset.moduleid] = e.target.value;
    saveState();
    $("select").filter(x => x.dataset.moduleid === e.target.dataset.moduleid)[0].focus();
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
  pre_events.filter(x => !x.room.startsWith("Übung ")).forEach(entry => {
    var id = find_id(grid, entry.starti, entry.endi);
    var obj = $$("summary.box-b-"+entry.id).classList;
    if (id !== 0) obj.add("conflicting");
  });
};

window.onload = function() {

  window.selectuebungs = {};

  window.module_by_id = {};
  data.forEach(x => module_by_id[x.id]=x);

  // put weekly events into
  window.pre_events = data
    .flatMap(x => x.weekly.map(y => ({
      id: x.id, title_short: x.title_short,
      count: y.count, day: y.day, start: y.start, end: y.end, room: y.room,
      starti: y.day * 24*60 + y.start[0] * 60 + y.start[1],
      endi:   y.day * 24*60 + y.end[0]   * 60 + y.end[1],
    })))
    .filter (x => x.count>1)
    // sort: longest duration first, then first start time first
    // important for displaying overlapping dates in calendar
    .sort((x,y) => ((y.endi-y.starti) - (x.endi-x.starti))*(7*24*60) + x.starti-y.starti);
  window.times = pre_events
    .flatMap(event => [event.starti, event.endi]);
  window.times = [...new Set(times)];
  times.sort((x,y) => x-y);
  pre_events.forEach(event => {
    event.starti = times.indexOf(event.starti);
    event.endi   = times.indexOf(event.endi);
  });

  // show modules
  window.lastCategory = null;

  // load state
  var course_uebung = location.hash.slice(1).split(";");
  var course = course_uebung[0].split(",");
  window.selectuebungs = JSON.parse(atob(course_uebung[1] || btoa("{}")));
  $("input").forEach(elem => {
    elem.checked = course.includes(elem.id.slice(8))
    if (elem.checked && elem.classList.length>0)
      elem.parentElement.nextElementSibling.classList.toggle(
        elem.classList[0].replace("er", "ed"));
  });

  // enable checkboxes
  $("input.checker").forEach( x => x.onclick = e => {
    x.parentElement.nextElementSibling.classList.toggle("checked");
    saveState();
  });

  // opening summary closes other summaries
  var modules = $(".module-wrapper > summary")
  modules.forEach(x => x.onclick = () =>
    modules.forEach(y =>
      x !== y ? y.parentElement.open = false : ""));

  // keyboard movement
  var esc = () => {
    var module = modules[modules.findIndex(x => x.parentElement.open)];
    if (module) module.click();
  };
  var prev = () => {
    var module = modules[modules.findIndex(x => x.parentElement.open)-1];
    if (module) module.click();
  };
  var next = () => {
    var module = modules[modules.findIndex(x => x.parentElement.open)+1];
    if (module) module.click();
  };
  document.onkeyup = (e) => {
    if      (e.keyCode === 27) esc();
    else if (e.keyCode === 37) prev();
    else if (e.keyCode === 39) next();
  };

  saveState();
}

