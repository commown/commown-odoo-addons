$(document).ready(function(){

    // Show/hide steps
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

    // Smart Wizard
    $('#smartwizard').smartWizard({
        selected: 0,
        keyNavigation: false,  // buggy (changes steps even when in an input)
        useURLhash: false,
        showStepURLhash: false,
        disabledSteps: [2, 3, 4],
        transitionEffect: 'slide',
        toolbarSettings: {
            toolbarPosition: 'top',
            toolbarButtonPosition: 'right',  // buggy: still on the left
        },
        lang: {
            next: 'Suivant',
            previous: 'Précédent',
        },
        anchorSettings: {
            markDoneStep: true, // add done css
            markAllPreviousStepsAsDone: false, // When a step selected by url hash, all previous steps are marked done
            removeDoneStepOnNavigateBack: true, // While navigate back done step after active step will be cleared
            enableAnchorOnDoneStep: true // Enable/Disable the done steps navigation
        }
    });

    $("#smartwizard").on("leaveStep", function(e, anchorObject, stepNumber, stepDirection) {
        var elmForm = $("#form-step-" + stepNumber);
        // stepDirection === 'forward' :- this condition allows to do the form validation
        // only on forward navigation, that makes easy navigation on backwards still do the validation when going next
        if(stepDirection === 'forward' && elmForm){
            elmForm.validator('validate');
            var elmErr = elmForm.children('.has-error');
            if(elmErr && elmErr.length > 0){
                // Form validation failed
                return false;
            }
        }
        return true;
    });

    $('#camera_model').change();
    $('#tighten_screws_solved_pb').change();

});
