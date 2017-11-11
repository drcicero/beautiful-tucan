window.onload = () => {
  var $  = x => Array.from(document.querySelectorAll(x));
  var $$ = x => document.querySelector(x);
  var addClass = c => e => e.classList.add(c);
  var delClass = c => e => e.classList.remove(c);

  function localStorageTest(){
    var test = 'test';
    try {
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch(e) {
      return false;
    }
  }

  let copy = it => JSON.parse(JSON.stringify(it));

  var categories = {};
  data.forEach(x => categories[x.category]=1);

  var lastCategory = null;
  function courseDiv(course) {
    var result = (
      "<span style=width:3em;color:red>" + course.credits + "CP</span>"
     +"<span style=width:3em>" + course.title_short + "</span>"
     +"<span style='width:calc( 100% - 2em - 3em - 5em - 2em )' title='"
       + course.title + "'>" + course.title + "</span>"
     +"<span style=width:5em;float:right;color:green title='"
       + course.owner + "'>" + course.owner_short + "</span>"
     +"<br>"
    );

//    if (course.clean_time && course.clean_time.length > 0)
//      result.push( "<small style=float:right>" + course.clean_time.map( x =>
//        x.count+"x "+x.day
//      ).join(", ") + "</small>" );
//    result.push("<clear/>")


//        <div class="input-item">
//          <div class="item" id="item-{{id}}"> </div>
//        </div>

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
    lastCategory = course.category;

    return category + (
        "<div class=course-wrapper>"
          + checker
          + "<div class=course id='course-" + course.id + "'>" + result + "</div>"
          + remover
      + "</div>"
      + "<div class=details id='details-" + course.id + "'>"
        + course.details.map( x => "<b>" + x.title + "</b><br/>" + x.details).join("<br/>\n")
      + "</div>"
    );
  }

  main.innerHTML = "<div class=category>" + data.map(courseDiv).join("\n") + "</div>";

  if (localStorageTest())
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) {
        elem.checked = x[1];
        if      (x[1] && elem.classList.contains("checker"))
          elem.parentElement.classList.add("checked");
        else if (x[1] && elem.classList.contains("remover"))
          elem.parentElement.classList.add("removed");
        else if (x[1] && elem.classList.contains("toggler"))
          elem.parentElement.classList.add("toggled");
      }
    });

  $("input.checker").forEach( x => x.onclick = () => {
    x.parentElement.classList.toggle("checked");
    localStorage.checked = JSON.stringify($("input").map(x => [x.id, x.checked]))
  });

  $("input.remover").forEach( x => x.onclick = () => {
    x.parentElement.classList.toggle("removed");
    localStorage.checked = JSON.stringify($("input").map(x => [x.id, x.checked]))
  });

  $("input.toggler").forEach( x => x.onclick = () => {
    x.parentElement.classList.toggle("toggled");
    localStorage.checked = JSON.stringify($("input").map(x => [x.id, x.checked]))
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

  remove_unchecked.onclick = ()=> {
    $(".hidden").forEach(delClass("hidden"));
    $("input.input")
    .filter(x => !x.checked)
    .forEach(x => {
      x.parentElement.classList.add("hidden");
      let y = document.getElementById("item2-" + x.id.substring(x.id.indexOf("-")))
      if (y) y.classList.add("hidden");
    });
  };

  show_all.onclick = () =>
    $(".hidden").forEach(delClass("hidden"));

}
