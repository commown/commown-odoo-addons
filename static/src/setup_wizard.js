function setUpWizard($container) {

    $container.smartWizard({
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

    $container.on("leaveStep", function(e, anchorObject, stepNumber, stepDirection) {
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

    var prefix = "form-step-";
    var required_fields = {};
    var widgets = ['input', 'select', 'radio', 'checkbox', 'textarea'];

    var selector = widgets.map(function(w) {return w + '[required]'}).join(',');

    $container.find('div[id*="form-step-"]').each(function(index, formContainer) {
        var step = formContainer.id.substring(prefix.length);
        required_fields[step] = $(selector, formContainer);
      });

    /**
     * Enable or disable a wizard step, handling required attributes
     * at the same time (i.e: unsetting required on fields which step
     * is disabled, resetting it if step is re-enabled)
     *
     * @param  {integer} number    0-index of the step.
     * @param  {boolean} enabled   0-index of the step.
     */
    $container.toggleStep = function(number, enabled) {
        $container.find("li").eq(number).toggleClass('disabled', !enabled);
        required_fields[number].attr('required', enabled ? 'required' : null);
        $container
            .find('div[id*="form-step-' + number + '"]')
            .find(widgets.join(','))
            .attr('disabled', enabled ? null : 'disabled');
    }

    return $container;

}
