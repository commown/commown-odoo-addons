$(function () {
    "use strict";
    $("button.cwn_bin_field_btn").click(function (ev) {
        ev.preventDefault();
        var $div = $(this).closest("div");
        $div.find("button.cwn_bin_field_btn").toggle();
        $div.find("a[download]").toggle();
        var $input = $div.find("input");
        $input.prop("disabled", !$input.prop("disabled"));
    });
});
