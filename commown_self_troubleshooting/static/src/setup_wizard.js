/* global $ */
// eslint-disable-next-line no-unused-vars
function setUpWizard($container) {
  /*
   * Utility vars and functions
   */

  const widgets = ['input', 'select', 'radio', 'checkbox', 'textarea'];
  const formStepIdPrefix = 'form-step-';
  const allStepsSelector = 'div[id*="' + formStepIdPrefix + '"]';

  function stepNumber(formContainer) {
    return parseInt(formContainer.id.substring(formStepIdPrefix.length), 10);
  }

  function computeRequiredFields() {
    const requiredFields = {};
    const selector = widgets.map(function(w) { return w + '[required]'; }).join(',');
    $container.find(allStepsSelector).each(function(index, formContainer) {
      requiredFields[stepNumber(formContainer)] = $(selector, formContainer);
    });
    return requiredFields;
  }

  function createHumanContactButton(contactStep) {

    function isStepEnabled(wizard, stepNumber) {
      return ! wizard.steps.eq(stepNumber).parent('li').hasClass('disabled');
    }

    function getCurrentState(wizard, $button) {
      return {
        text: $button.text(),
        stepStates: $.map(wizard.steps, function(step, stepIndex) {
          return isStepEnabled(wizard, stepIndex);
        }),
        currentStep: wizard.current_index,
      };
    }

    function setState(wizard, $button, state) {
      $button.text(state.text);
      $.each(wizard.steps, function(stepIndex, step) {
        wizard.toggleStep(stepIndex, state.stepStates[stepIndex]);
      });
      wizard.goToStep(state.currentStep);
    }

    var previousState;

    return $('<button/>').text('Contacter un humain')
      .addClass('btn btn-warning')
      .on('click', function(event) {
        event.preventDefault();
        const $button = $(this);
        const wizard = $container.data('smartWizard');

        if (!isStepEnabled(wizard, contactStep)) {
          previousState = getCurrentState(wizard, $button);
          setState(wizard, $button, {
            text: "Revenir à l'auto-dépannage",
            stepStates: $.map(wizard.steps, function(step, stepIndex) {
              return stepIndex === contactStep;
            }),
            currentStep: contactStep,
          });
          $('.sw-btn-group').hide();
        }
        else {
          setState(wizard, $button, previousState);
          $('.sw-btn-group').show();
        }
      });
  }

  // Let's setup the wizard

  let contactStep = null;
  const extraButtons = [];
  const requiredFields = computeRequiredFields();
  const buttonI18n = {
    fr: {
      previous: 'Précédent',
      next: 'Suivant',
    },
    de: {
      previous: 'Vorheriger Schritt',
      next: 'Nächster Schritt',
    }
  };

  const $humanContactButton = $container.find('button[value="contact"]');
  if ($humanContactButton.length) {
    contactStep = stepNumber($humanContactButton.closest(allStepsSelector)[0]);
    extraButtons.push(createHumanContactButton(contactStep));
  }

  $container.smartWizard({
    selected: 0,
    keyNavigation: false,
    useURLhash: false,
    showStepURLhash: false,
    transitionEffect: 'slide',
    toolbarSettings: {
      toolbarPosition: 'top',
      toolbarButtonPosition: 'end', // does not work with bootstrap 3!
      toolbarExtraButtons: extraButtons,
    },
    theme: 'arrows',
    lang: buttonI18n[$("html").attr("lang").split("-")[0]],
    anchorSettings: {
      markDoneStep: true,
      markAllPreviousStepsAsDone: false,
      removeDoneStepOnNavigateBack: true,
      enableAnchorOnDoneStep: true,
    },
  });

  $container.on('leaveStep', function(e, anchorObject, stepNum, stepDirection) {
    const elmForm = $('#' + formStepIdPrefix + stepNum);
    if (stepDirection === 'forward' && elmForm) {
      elmForm.validator('validate');
      const elmErr = elmForm.find('.form-group.has-error');
      if (elmErr && elmErr.length > 0) {
        return false;
      }
    }
    return true;
  });

  /**
   * Enable or disable a wizard step, handling required attributes
   * at the same time (i.e: unsetting required on fields which step
   * is disabled, resetting it if step is re-enabled)
   *
   * @param  {integer} number    0-index of the step.
   * @param  {boolean} enabled   0-index of the step.
   */
  const wizard = $container.data('smartWizard');
  wizard.toggleStep = function(number, enabled) {
    $container.find('li').eq(number).toggleClass('disabled', !enabled);
    if (requiredFields[number] !== undefined) {
      requiredFields[number].attr('required', enabled ? 'required' : null);
    }
    $container
      .find('#' + formStepIdPrefix + number)
      .find(widgets.join(','))
      .attr('disabled', enabled ? null : 'disabled');
  };

  if (contactStep !== null) {
    wizard.toggleStep(contactStep, false);
  }

  return wizard;
}
