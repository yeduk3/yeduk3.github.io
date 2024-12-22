// $('.sidebar').on('click', function(e) {
//     if($(e.target).is('a')) {
//         var str = e.target.innerText;
//         // console.log(str);
//         str = str.toLowerCase();
//         $('.markdown-body').attr('src', '/main/aboutme_' + str + '.md');
//     }
// });

var sidebarList = document.querySelectorAll(".sidebar");
// console.log(sidebarList)

for (var sidebar of sidebarList) {
  sidebar.addEventListener("click", function (event) {
    if (event.target.tagName == "A") {
      var curContent = event.target.parentNode.parentNode.parentNode.parentNode;
      var contentName = curContent.classList[0];

      var selected = event.target.textContent.toLowerCase().replace(" ", "");
      curContent
        .getElementsByClassName("markdown-body")[0]
        .setAttribute("src", "/main/" + contentName + "_" + selected + ".md");
    }
  });
}
