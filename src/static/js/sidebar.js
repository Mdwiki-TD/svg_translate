
function toggleSidebar() {
    const sidebar = document.querySelector('.colmd2');
    const content = document.querySelector('.colmd10');

    sidebar.classList.toggle('collapsed1');
    content.classList.toggle('expanded');

    // add collapsed-toggle-btn to main-toggle-btn class
    $(".main-toggle-btn>i").toggleClass('collapsed-toggle-btn');
}

$(document).ready(function () {
    $(".Dropdown_menu_toggle").on("click", function () {
        $(".div_menu").toggleClass("mactive");
        // ---
        $(".Dropdown_menu_toggle").text($(".div_menu").hasClass("mactive") ? "✖ Close Sidebar" : "☰ Open Sidebar");
    });

});
