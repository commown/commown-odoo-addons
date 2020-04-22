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
    return $('<button/>').text('Contacter un humain !')
      .addClass('btn btn-warning')
      .on('click', function(event) {
        event.preventDefault();
        const wizard = $container.data('smartWizard');
        $.map(wizard.steps, function(step, stepIndex) {
          if (stepIndex !== contactStep) {
            $container.toggleStep(stepIndex, false);
            wizard.stepState(stepIndex, 'disable');
          }
        });
        $container.toggleStep(contactStep, true);
        wizard.goToStep(contactStep);
      });
  }

  // Let's setup the wizard

  let contactStep = null;
  const extraButtons = [];
  const requiredFields = computeRequiredFields();

  const $humanContactButton = $container.find('button[value="contact"]');
  if ($humanContactButton.length) {
    contactStep = stepNumber($humanContactButton.closest(allStepsSelector)[0]);
    extraButtons.push(createHumanContactButton(contactStep));
  }

  const wizard = $container.smartWizard({
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
    lang: {
      next: 'Suivant',
      previous: 'Précédent',
    },
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
