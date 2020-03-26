$(document).ready(function(){

    $('#camera_model').change(function () {
        if (this.value === 'new') {
            $('#tighten_screws_solved_pb').attr('required', 'required');
        } else {
            $('#tighten_screws_solved_pb').removeAttr('required');
        }
        $("#smartwizard li").eq(2).toggleClass('disabled', this.value!=='new');
        $("#smartwizard li").eq(3).toggleClass('disabled', this.value!=='old');
        $("#smartwizard li").eq(4).toggleClass('disabled', this.value!=='old');
    });

    $('#tighten_screws_solved_pb').change(function () {
        $("#smartwizard li").eq(3).toggleClass('disabled', this.value!=='no');
        $("#smartwizard li").eq(4).toggleClass('disabled', this.value!=='no');
    });

    $('#camera_model').change();
    $('#tighten_screws_solved_pb').change();

});
