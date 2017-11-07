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
}
