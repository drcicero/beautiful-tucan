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

  if (localStorageTest())
    JSON.parse(localStorage.checked || "[]").forEach(x => {
      var elem = document.getElementById(x[0]);
      if (elem) elem.checked = x[1];
    });

  $(".tab").forEach( x => x.onclick = () => {
    $(".tab-active").forEach(delClass("tab-active"));
    x.classList.add("tab-active");
    $(".supercategory").forEach(addClass("hidden"));
    $$("#supercategory-" + x.htmlFor).classList.remove("hidden");
  })

  $("input").forEach( x => x.onclick = () =>
    localStorage.checked = JSON.stringify($("input").map(x => [x.id, x.checked])) );

  $(".item").map( x => x.onclick = e => {
    var id = e.currentTarget.id.substring(e.currentTarget.id.indexOf("-")+1);
    $(".active").forEach(delClass("active"));
    $$("#item-" + id).classList.add("active");
    $$("#details-" + id).classList.add("active");
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

  let copy = it => JSON.parse(JSON.stringify(it));

  var categories = {};
  data.forEach(x => categories[x.category]=1);

  var lastCategory = null;
  function courseDiv(course) {
    var result = [];

    result.push(
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

    var category = lastCategory == course.category ? "" :
      "<br><div><b>" + course.category + "</b></div>";
    lastCategory = course.category;
    return category + "<div class=course id='" + course.id + "'>" + result.join("") + "</div>";
  }

  main.innerHTML = data.map(courseDiv).join("\n");
}
