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


// use localStorage
function saveState() {
  if (hasLocalStorage) localStorage.checked =
    JSON.stringify($("input").map(x => [x.id, x.checked]))

  var selected = $("input.checker")
    .filter(elem   => elem.checked)
    .map   (elem   => course_by_id[elem.id.substring(elem.id.indexOf("-")+1)]);

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

    var selectedweekly = selected
      //.filter(x => x.weekly.length>0)
      .map(x =>
          x.weekly.map(y =>
              y.time[0] + "" + y.count+ "x " + y.day +" "+ y.start +" - "+ y.end +" "+
              x.title_short +" ("+ y.room +")" ))
          .reduce((x,y) => x.concat(y))
      .sort()
      .map( x => x.substring(1) );

    termine = (""
      + "Termine liegen zwischen "
      + first.getDate() +"."+ first.getMonth() +"."+ first.getFullYear()
      + " und "
      + last.getDate() +"."+ last.getMonth() +"."+ last.getFullYear()
      + ":<br/>"
      + selectedweekly.join("<br/>")
      + "<br/>"
      + "<br/>"
    );
  }

  var events = pre_events.filter(x => selected.some(y => y.id == x.id));
  var assoc = new Map();
  var grid = {};
  events.forEach(event =>
    assoc.set(event.time, allocate(grid, event.start, event.end))
  );
  var found = {size:Math.max.apply(Math, [0, ...(grid[0]||[])])};
  var subblock = [found];
  for (var t=1; t<times.length; t++) {
    if (noCommonElement(grid[t]||[], grid[t-1]||[])) found = {size:0};
    if (grid[t]) found.size = Math.max.apply(Math, [found.size, ...grid[t]]);
    subblock[t] = found;
  }

  var box = main2.getClientRects()[0];
  var width  = box.width-50;
  var height = 480;

  main2.innerHTML = (""
//    + "Für Regelstudienzeit sind durchschnittlich jedes Semester 30 CP vorgesehen.<br>"
    + "Du hast "
    + selected
      .map   (course => parseInt(course.credits))
      .reduce((x,y) => x+y, 0)
    +" CP in folgenden Kursen ausgewählt:<br>"
    + selected.map   (course => course.title_short).join(", ")
    + "<br><br>"

    + "Wochen-Kalender:"
    + "<table style=width:100%><td style=width:20%>Mo</td><td style=width:20%>Di</td><td style=width:20%>Mi</td><td style=width:20%>Do</td><td style=width:20%>Fr</td></table>"

    + "<div style='position:relative;background:#eee;width:"+width+"px;height:"+height+"px;font-size:0.8em'>"
    + [0,1,2,3,4].map( d=> [...Array(7).keys()].map( h =>
        "<div class=box-c style="+
        "'width:"+(width/5-10)+"px;top:"+(h*73.33)+"px;left:"+(d*width/5)+"px'></div>"
      ).join("")).join("\n")
    + selected.map( (select,i) => select.weekly.map( week => {
      var parallelBlocks = subblock[
        times.indexOf(week.time[0]*24*60 + week.time[1][0]*60 + week.time[1][1])
      ].size+1;
      var lshift = width/5/parallelBlocks * assoc.get(week.time);
      var left   = width/5      * week.time[0] + lshift;
      var top    = height/12/60*10 * ((week.time[1][0]-8) * 60 + week.time[1][1])/ 10;
      var h      = height/12/60*10 * ((week.time[2][0]-8) * 60 + week.time[2][1])/ 10 - top;
      var w      = width/5/parallelBlocks - 10;
      var desc = select.title_short + " - " + week.time[1][0]+":"+week.time[1][1]+" - "+week.time[2][0]+":"+week.time[2][1]+"<br>"+week.room+"<br>findet "+week.count+" Mal statt";
      var class_ = " class='box-b box-b-" + select.id + " color-" + (data.indexOf(select)%colors.length) + "'";
      var title  = " title='" + desc.replace(/<br>/g, "\n") + "\n" + select.title + "'";
      var style  = " style='position:absolute;top:"+top+"px;left:"+left+"px;width:"+w+"px;height:"+h+"px'";
      return "<div" + class_ + title + style + ">" + desc + "</div>";
    } ).join("\n")).join("\n")
    + "</div><br>"

//    + selected
//      .map   (course => "* " + course.credits +"CP "+ course.title)
//      .join("<br/>")
//    +"<br/><br/>"
  
    + termine
    + selected.map(x => x.title_short +": "+ x.title).join("<br/>")
  );

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
  pre_events.forEach(entry => {
    var id = find_id(grid, entry.start, entry.end);
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
          "* " + x.count +"x "+ x.day +" "+ x.start +" - "+ x.end +" ("+ x.room +")"
        ).join("<br/>")
      + "<br/><br/>";
  details += "<b>Kurse</b><br/>" + course.content.map(x=>x.title).join("<br/>\n")+"<br/><br/>"
  details += course.details.filter(x=>x.details != "").map( x =>
    "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n");

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

//  // gather categories
//  window.categories = {};
//  data.forEach(x => categories[x.category]=1);
  window.course_by_id = {};
  data.forEach(x => course_by_id[x.id]=x);

  window.pre_events = data
    .map   (x => x.weekly.map(y => ({
      id: x.id,  title_short: x.title_short,
      start: y.time[0] * 24*60 + y.time[1][0] * 60 + y.time[1][1],
      end:   y.time[0] * 24*60 + y.time[2][0] * 60 + y.time[2][1],
      time:  y.time,
      count: y.count,
    })))
    .reduce((x,y)=>x.concat(y), [])
    .filter (x => x.count>1)
    .sort((x,y) => ((y.end-y.start) - (x.end-x.start))*(5*24*60) + x.start-y.start);
  window.times = pre_events
    .map   (event => [event.start, event.end])
    .reduce((x,y) => x.concat(y), []);
  times = [...new Set(times)];
  times.sort((x,y) => x-y);
  pre_events.forEach(event => {
    event.start = times.indexOf(event.start);
    event.end   = times.indexOf(event.end);
  });

  // show courses
  window.lastCategory = null;
  main.innerHTML = "<div><details hidden>" + data.map(courseDiv).join("\n") + "</details></div>";

  // load state
  if (hasLocalStorage)
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) elem.checked = x[1];
      if (elem && elem.classList.length>0 && x[1]) elem.parentElement.nextSibling.classList.toggle(
        elem.classList[0].replace("er", "ed"));
    });

  // enable toggles
  $("input.checker").forEach( x => x.onclick = e => {
    x.parentElement.nextSibling.classList.toggle("checked");
    saveState();
//    x.parentElement.parentElement.open = !x.parentElement.parentElement.open; // BUG workaround
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
