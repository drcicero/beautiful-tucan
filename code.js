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
//var addClass = c => e => e.classList.add(c);
//var copy = it => JSON.parse(JSON.stringify(it));

var colors = ["#dc4444", "#9066d9", "#03A9F4", "#439646", "#FFEB3B", "#FF5722",
              "#E91E63", "#00BCD4", "#8BC34A", "#FFC107", "#795548", "#9C27B0",
              "#2196F3", "#009688", "#CDDC39", "#FF9800"];

// do grid[t].push(id) for min_t<t<max_t where a number 'id' that is not yet
// inside any grid[t]; and return the id.
var allocate = (grid, entry, min_t, max_t) => {
  for (var id=0; id<20; id++) {
    var ok = true;
    for (var t=min_t; t<max_t; t++) ok = ok && !(t+"-"+id in grid);
    if (ok) break;
  }

  for (var t=min_t; t<max_t; t++) grid[t+"-"+id] = entry;

  for (var t=min_t; t<max_t; t++) {
    if (!(t in grid)) grid[t] = [];
    grid[t].push(id)
  }

  return id;
}

// use localStorage
var saveState = function() {
  if (hasLocalStorage) localStorage.checked =
    JSON.stringify($("input").map(x => [x.id, x.checked]))

  var selected = $("input.checker")
    .filter(elem   => elem.checked)
    .map   (elem   => course_by_id[elem.id.substring(elem.id.indexOf("-")+1)]);

  var first = new Date(selected
    .map   (course => +new Date(course.first))
    .filter(x      => x)
    .reduce((x,y)  => Math.min(x, y)));

  var last = new Date(selected
    .map   (course => +new Date(course.last))
    .filter(x      => x)
    .reduce((x,y)  => Math.max(x, y)));

  var selectedweekly = selected
//    .filter(x => x.weekly.length>0)
    .map(x => x.weekly.map(y =>
      y.day_nr + "* " + y.day +" "+ y.start +" - "+ y.end +" "+ x.title_short +" ("+ y.room +"), insgesamt " + y.count + " mal" ))
    .reduce((x,y) => x.concat(y));

  selectedweekly.sort();
  selectedweekly = selectedweekly.map( x => x.substring(1) );

  var events = selected
    .map   (x => x.weekly.map(y => ({
      id:    x.title_short,
      start: y.time[0] * 24*60 + y.time[1][0] * 60 + y.time[1][1],
      end:   y.time[0] * 24*60 + y.time[2][0] * 60 + y.time[2][1],
      time:  y.time,
      count: y.count,
    })))
    .reduce((x,y)=>x.concat(y))
    .filter (x => x.count>1);
  events.sort((x,y) => ((y.end-y.start) - (x.end-x.start))*(5*24*60) + x.start-y.start);
  var times = events
    .map   (event => [event.start, event.end])
    .reduce((x,y) => x.concat(y));
  times = [...new Set(times)];
  times.sort((x,y) => x-y);
  events.forEach(event => {
    event.start = times.indexOf(event.start);
    event.end   = times.indexOf(event.end);
  });
  var assoc = new Map();
  var grid = {};
  events.forEach(event =>
    assoc.set(event.time, allocate(grid, event.id, event.start, event.end)));

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
    + "Es wird empfohlen jedes Semester durchschnittlich 30 CP zu machen.<br>"
    + "Du hast "
    + selected
      .map   (course => parseInt(course.credits))
      .reduce((x,y) => x+y)
    +" CP in folgenden Kursen ausgewählt:<br>"
    + selected.map   (course => course.title_short).join(", ") + "."
    + "<br><br>"

    + "Wochen-Kalender:"
    + "<table style=width:100%><td style=width:20%>Mo</td><td style=width:20%>Di</td><td style=width:20%>Mi</td><td style=width:20%>Do</td><td style=width:20%>Fr</td></table>"

    + "<div style='position:relative;background:#eee;width:"+width+"px;height:"+height+"px;font-size:.5em'>"
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
      var desc = select.title_short+"<br>"+week.time[1][0]+":"+week.time[1][1]+" - "+week.time[2][0]+":"+week.time[2][1]+"<br>"+week.room;
      return ("<div class=box-b title='"+desc.replace(/<br>/g, "  ")+"' style='position:absolute;"
        +"background:"+colors[i%colors.length]+";"
        +"top:"+top+"px;left:"+left+"px;width:"+w+"px;height:"+h+"px'>"
        +desc+"</div>");
    } ).join("\n")).join("\n")
    + "</div><br>"

//    + selected
//      .map   (course => "* " + course.credits +"CP "+ course.title)
//      .join("<br/>")
//    +"<br/><br/>"
    + "Termine liegen zwischen "
    + first.getDate() +"."+ first.getMonth() +"."+ first.getFullYear()
    + " und "
    + last.getDate() +"."+ last.getMonth() +"."+ last.getFullYear()
    + ":<br/>"
    + selectedweekly.join("<br/>")
  );
};

// create div from course
window.lastCategory = null;
var courseDiv = (course) => {
  var result = (
    "<span style=width:3em;color:red>" + course.credits + "CP</span>"
  + "<span style=width:3em>" + course.title_short + "</span>"
  + "<span style='width:calc( 100% - 2em - 3em - 5em - 2em )' title='"
     + course.title + "'>" + course.title + "</span>"
  + "<span style=width:5em;float:right;color:green title='"
     + course.owner + "'>" + course.owner_short + "</span>"
  + "<br/>"
  );

  var checker = '<input class=checker type="checkbox" id="checker-' + course.id + '"/>'
              + '<label class=checker for="checker-' + course.id + '"></label>';
  var remover = '<input class=remover type="checkbox" id="remover-' + course.id + '"/>'
              + '<label class=remover for="remover-' + course.id + '">X</label>';

  var cat = course.category.replace(' ', '-');
  var category = (lastCategory == course.category ? "" :
      '<br/></div><div class=category>'
    + '<input class=toggler type="checkbox" id="toggler-' + cat + '"/>'
    + '<label class=toggler for="toggler-' + cat + '"><div class=toggler-show></div>'
    + '<b>' + course.category + '</b><clear/></label>'
  );
  window.lastCategory = course.category;

  var details = "";
  if (course.weekly && course.weekly.length > 0)
    details += "<b>" + course.first_to_last + "</b>"
      + course.weekly.map( x =>
          "* " + x.count +"x "+ x.day +" "+ x.start +" - "+ x.end +" ("+ x.room +")"
        ).join("<br/>")
      + "<br/><br/>";
  details += course.details.map( x =>
    "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n");

  return category + (
    "<div class=course-wrapper>"
      + checker
      + "<div class=course id='course-" + course.id + "'>" + result + "</div>"
      + remover
  + "</div>"
  + "<div class=details id='details-" + course.id + "'>"
    + details
  + "</div>"
  );
}


window.onload = function() {

//  // gather categories
//  window.categories = {};
//  data.forEach(x => categories[x.category]=1);
  window.course_by_id = {};
  data.forEach(x => course_by_id[x.id]=x);

  // show courses
  window.lastCategory = null;
  main.innerHTML = "<div class=category>" + data.map(courseDiv).join("\n") + "</div>";

  // load state
  if (hasLocalStorage)
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) elem.checked = x[1];
      if (elem && elem.classList.length>0 && x[1]) elem.parentElement.classList.toggle(
        elem.classList[0].replace("er", "ed"));
    });

  // enable toggles
  $("input.checker, input.remover, input.toggler").forEach( x => x.onclick = function() {
    x.parentElement.classList.toggle(x.classList[0].replace("er", "ed"));
    saveState();
  });
  $(".course").map( x => x.onclick = e => {
    var id = e.currentTarget.id.substring(e.currentTarget.id.indexOf("-")+1);
    var toggle_on = !x.classList.contains("active");
    $(".active").forEach(delClass("active"));
    if (toggle_on) {
      $$("#course-" + id).classList.add("active");
      $$("#details-" + id).classList.add("active");
    }
  });

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

}
