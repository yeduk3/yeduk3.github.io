var content = document.querySelector("#content");

var jsonXHR = new XMLHttpRequest();
jsonXHR.open("get", "/main/main_data.json");
jsonXHR.onload = () => {
  var jsonobj = jsonXHR.responseText;
  jsonobj = JSON.parse(jsonobj);

  var data = jsonobj["data"];

  for (var d of data) {
    var dataXHR = new XMLHttpRequest();
    dataXHR.open("get", d["HTMLURL"], false);
    dataXHR.onload = () => {
      var div = document.createElement("div");
      div.classList.add(d["name"]);
      div.classList.add("hidden");
      div.innerHTML = dataXHR.responseText;
      content.appendChild(div);

      if (d["hasJS"]) {
        var scr = document.createElement("script");
        scr.type = "text/javascript";
        scr.src = d["JSURL"];
        content.appendChild(scr);
      }
    };
    dataXHR.send();
  }
};
jsonXHR.onloadend = () => {
  var contentList = document.querySelectorAll("#content div");
  contentList[1].classList.remove("hidden");
  // console.log(contentList[1]);
};
jsonXHR.send();
