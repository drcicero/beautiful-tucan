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
  element.href = "data:text/plain;charset=utf-8," + encodeURIComponent(text);
  element.download = filename;
  element.textContent = linktext;
  return element;
}

var ical = {
  vdt: d => d.getFullYear()
            + (d.getMonth()+1+"").padStart(2,'0')
            + (d.getDate()+"").padStart(2,'0')
            + "T"
            + (d.getHours()+"").padStart(2,'0')
            + (d.getMinutes()+"").padStart(2,'0')
            + (d.getSeconds()+"").padStart(2,'0'),

  ymd: d => d.getFullYear() + "-"
            + (d.getMonth()+1+"").padStart(2,'0') + "-"
            + (d.getDate()+"").padStart(2,'0'),

  vcalendar: function (dates) {
    var dates = dates.map(date => {
      var x = date.split("\t");
      return {start:new Date(x[0] + "T" + x[1]),
              end: new Date(x[0] + "T" + x[2]),
              title: x[4],
              location: x[3],};
    });

    return "BEGIN:VCALENDAR"
      + "\nPRODID:-//Beautiful Tucan via Javascript//DE"
      + "\nVERSION:2.0"
      + "\nBEGIN:VTIMEZONE"
      + "\nTZID:Europe/Berlin"
      + "\nBEGIN:DAYLIGHT"
      + "\nTZOFFSETFROM:+0100"
      + "\nTZOFFSETTO:+0200"
      + "\nTZNAME:CEST"
      + "\nDTSTART:19700329T020000"
      + "\nRRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3"
      + "\nEND:DAYLIGHT"
      + "\nBEGIN:STANDARD"
      + "\nTZOFFSETFROM:+0200"
      + "\nTZOFFSETTO:+0100"
      + "\nTZNAME:CET"
      + "\nDTSTART:19701025T030000"
      + "\nRRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10"
      + "\nEND:STANDARD"
      + "\nEND:VTIMEZONE"
      + dates.map(ical.vevent).join("")
      + "\nEND:VCALENDAR";
  },

  vevent: function (date) {
    return ""
      + "\nBEGIN:VEVENT"
      + "\nUID:" + Math.floor(Math.random()*0xffffffff).toString(16)
      + "\nDTSTAMP:" + ical.vdt(new Date())
      + "\nDTSTART;TZID=Europe/Berlin:" + ical.vdt(date.start)
      + "\nDTEND;TZID=Europe/Berlin:"   + ical.vdt(date.end)
      + "\nSUMMARY:" + date.title
      + "\nLOCATION:" + date.location
      + "\nEND:VEVENT";
  }
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

    var calendardates = selected
      .flatMap(module => Object.values(module.content).map(x => [module, x]))
      .flatMap(x => [
        ...x[1].dates
          .map(y => y + "\t" + x[0].title_short),
        ...x[0].weekly
          .filter(w => w.room.startsWith("Übung ") && selectuebungs[x[0].id] === format_weekly(w)
                    || w.room.startsWith("Übungsstunde"))
          .flatMap(y =>
            [...Array(y.count).keys()].map(i =>
              ical.ymd(new Date(+new Date(y.firstdate) + 1000*60*60*24*7 * i))
            + "\t"+ format_timespan(y).replace(" - ", "\t") +"\t-\tÜbung " + x[0].title_short) )
      ]);

    termine = (""
      + genDownloadLink(ical.vcalendar(calendardates),
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
    + "Du hast "
    + selected
      .map   (module => parseInt(module.credits))
      .reduce((x,y) => x+y, 0)
    +" CP in folgenden Kursen ausgewählt:<br>"
    + selected.map(module => module.title_short + " (" + parseInt(module.credits) + "cp)").join(", ")
    + "<br><br>"

    + (possibleUebungs.length === 0 ? "" :
        "Kleingruppen wählen:<br>"
      + possibleUebungs.map(kv =>
        module_by_id[kv[0]].title_short
        + ": <select data-moduleid='"+kv[0]+"'><option>Kleingruppentermin wählen</option>"
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
    + "</div><br>"
    + termine
    + selected.map(x => x.title_short +": "+ x.title).join("<br/>")
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

// create div from module
//window.lastSuperCategory = null;
function moduleDiv(module) { // writes to window.lastCategory
  var result = (
    "<span>" + module.credits + "CP</span>"
  + "<span>" + module.title_short + "</span>"
  + "<span title='"
     + module.title + "'>" + module.title + "</span>"
  + "<span title='"
     + module.owner + "'>" + module.owner_short + "</span>"
  );

  var checker = '<label><input class=checker type="checkbox" id="checker-' + module.id + '"/></label>';

  var cat = module.category.replace(' ', '-');
  var category = (lastCategory == module.category ? "" :
      '\n<br/>'
    + '\n</details>'
    + '\n<details class=category open>'
    + '\n  <summary>'
    + '\n    <div class=toggler-show></div>'
    + '\n    <b>' + module.category + '</b>'
    + '\n    <clear/>'
    + '\n  </summary>'
  );
  window.lastCategory = module.category;

  //  var cat = module.category.replace(' ', '-');
  //  var category_start_html = ('<div class=category>'
  //    + '<input class=toggler type="checkbox" id="toggler-' + cat + '"/>'
  //    + '<label class=toggler for="toggler-' + cat + '"><div class=toggler-show></div>'
  //    + '<b>' + (module.category[0]=="Y" ? module.category.slice(14) : module.category) + '</b><clear/></label>');

  //  var category = (lastSuperCategory == (module.category[0]=="Y") ? (lastCategory == module.category ? "" :
  //      '<br/></div>' + category_start_html
  //  ) :
  //      '<br/></div></div><div class=category>'
  //    + '<input class=toggler type="checkbox" id="toggler-' + (module.category[0]=="Y") + '"/>'
  //    + '<label class=toggler for="toggler-' + (module.category[0]=="Y") + '"><div class=toggler-show></div>'
  //    + '<b>' + module.category[0] + '</b><clear/></label>' + category_start_html );
  //  window.lastSuperCategory = module.category[0]=="Y";
  //  window.lastCategory = module.category;

  var details = ""; // "<div class=esc>X</div><div class=prev>&lt;</div><div class=next>&gt;</div>";

  if (module.weekly && module.weekly.length > 0) {
    var dates = Object.values(module.content)
      .flatMap(course => [...course.dates, ...course.uedates])
      .map(x => x.split("\t")[0]);
    details += "<b>Termine liegen zwischen " + first_to_last(dates) + "</b><br>"
      + module.weekly.map( x =>
          "* " + x.count +"x " + (x.count == 1? x.firstdate + " ": "") + format_weekly(x) +" ("+ x.room +")"
        ).join("<br/>")
      + "<br/><br/>";
  }
  details += "<b>Kurse</b><br/>" +
    Object.values(module.content).map(x=>x.title).join("<br/>\n")+"<br/><br/>"
  details += module.details.filter(x=>x.details != "").map( x =>
    "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n");
  details += "<br/><hr/><br/>" +
    Object.values(module.content).map(x=>
      "<b>" + x.title + "</b><br/>\n" + x.details.map(x=>
      "<i>" + x.title + "</i>:\n" + x.details).join("<br/><br/>\n")).join("<br/><br/><br/>\n") +
    "<br/><br/>";
  // details += JSON.stringify(module.uedates);

  return category + (""
    +"\n<div class=flex>"
    +"\n  " + checker
    +"\n  <details class=module-wrapper style=''>"
    +"\n    <summary id='module-" + module.id + "' class='module box-b box-b-" + module.id + "'>"
    +"\n      " + result
    +"\n      <div class=toggler-show></div>"
    +"\n    </summary>"
    +"\n    <div class=details id='details-" + module.id + "'>"
    +"\n      " + details
    +"\n    </div>"
    +"\n  </details>"
    +"\n</div>"
  );
}

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
  main.innerHTML = "<div><details hidden>"
    + data.map(moduleDiv).join("\n") // writes to window.lastCategory
    + "</details></div>";

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
  $(".module-wrapper > summary").forEach(x => x.onclick = () =>
    $(".module-wrapper > summary").forEach(y =>
      x !== y ? y.parentElement.open = false : ""));

  // keyboard movement
  var esc = () => {
    var modules = $(".module-wrapper > summary");
    modules[modules.findIndex(x => x.parentElement.open)].click();
  };
  var prev = () => {
    var modules = $(".module-wrapper > summary");
    modules[modules.findIndex(x => x.parentElement.open)-1].click();
  };
  var next = () => {
    var modules = $(".module-wrapper > summary");
    modules[modules.findIndex(x => x.parentElement.open)+1].click();
  };
  document.onkeyup = (e) => {
    if      (e.keyCode === 27) esc();
    else if (e.keyCode === 37) prev();
    else if (e.keyCode === 39) next();
  };

  saveState();
}

