$(function() {

    $('#smartwizard').smartWizard({
        selected: 0,
        keyNavigation: false,  // buggy (changes steps even when in an input)
        useURLhash: false,
        showStepURLhash: false,
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

});
