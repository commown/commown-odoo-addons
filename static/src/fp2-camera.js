/* global $ */
$(document).ready(function() {

    const wizard = setUpWizard($('#smartwizard'));

    $('#camera_model').change(function () {
        wizard.toggleStep(2, this.value==='new');
        wizard.toggleStep(5, this.value==='new');
    });

    $('#tighten_screws_solved_pb').change(function () {
        wizard.toggleStep(3, this.value==='no');
        wizard.toggleStep(4, this.value==='no');
        wizard.toggleStep(5, this.value==='yes');
    });

});
