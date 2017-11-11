try {
  localStorage.setItem('test', 'test');
  localStorage.removeItem('test');
  window.hasLocalStorage = true;
} catch(e) {
  window.hasLocalStorage = false;
}

var saveState = function() {
  if (hasLocalStorage) localStorage.checked =
    JSON.stringify($("input").map(x => [x.id, x.checked]))
};

var $  = x => Array.from(document.querySelectorAll(x));
var $$ = x => document.querySelector(x);
var addClass = c => e => e.classList.add(c);
var delClass = c => e => e.classList.remove(c);
var copy = it => JSON.parse(JSON.stringify(it));

window.lastCategory = null;
var courseDiv = (course) => {
  var result = (
    "<span style=width:3em;color:red>" + course.credits + "CP</span>"
  + "<span style=width:3em>" + course.title_short + "</span>"
  + "<span style='width:calc( 100% - 2em - 3em - 5em - 2em )' title='"
     + course.title + "'>" + course.title + "</span>"
  + "<span style=width:5em;float:right;color:green title='"
     + course.owner + "'>" + course.owner_short + "</span>"
  + "<br>"
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
    details += (
      "<b>" + course.first_to_last + "</b>"
    + course.weekly.map( x =>
        "* " + x.count +"x "+ x.day +" "+ x.start +" - "+ x.end +" ("+ x.room +")"
      ).join("<br/>")
    + "<br/><br/>"
    );
  details += (
    course.details.map( x => "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n")
  );

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

  window.lastCategory = null;
  main.innerHTML = "<div class=category>" + data.map(courseDiv).join("\n") + "</div>";

  if (hasLocalStorage)
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) elem.checked = x[1];
      if (elem && elem.classList.length>0 && x[1]) elem.parentElement.classList.toggle(
        elem.classList[0].replace("er", "ed"));
    });

  var categories = {};
  data.forEach(x => categories[x.category]=1);

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
