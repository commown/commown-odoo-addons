$(document).ready(function(){

    $('#camera_model').change(function () {
        $('#tighten_screws_solved_pb').attr('required', this.value!=='old' ? 'required' : null)
        $("#smartwizard li").eq(2).toggleClass('disabled', this.value!=='new');
        $("#smartwizard li").eq(3).toggleClass('disabled', this.value!=='old');
        $("#smartwizard li").eq(4).toggleClass('disabled', this.value!=='old');
        $('input[name="screwdriver"]').attr('required', this.value==='old' ? 'required' : null)
    });

    $('#tighten_screws_solved_pb').change(function () {
        $("#smartwizard li").eq(3).toggleClass('disabled', this.value!=='no');
        $("#smartwizard li").eq(4).toggleClass('disabled', this.value!=='no');
        $('input[name="screwdriver"]').attr('required', this.value==='no' ? 'required' : null)
        $("#smartwizard li").eq(5).toggleClass('disabled', this.value!=='yes');
    });

    $('#camera_model').change();
    $('#tighten_screws_solved_pb').change();

});
