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

  function setupHumanContactButton(contactStep) {

    function isStepEnabled(wizard, stepNumber) {
      return ! wizard.steps.eq(stepNumber).hasClass('disabled');
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

    return $('button#contactAHuman')
      .on('click', function(event) {
        event.preventDefault();
        const $button = $(this);
        const wizard = $container.data('smartWizard');
        $container.toggleClass('contact-human');
        // Important when coming from an invalid form step:
        $container.toggleClass('was-validated', false);

        if (!isStepEnabled(wizard, contactStep)) {
          previousState = getCurrentState(wizard, $button);
          setState(wizard, $button, {
            text: "Revenir à l'auto-dépannage",
            stepStates: $.map(wizard.steps, function(step, stepIndex) {
              return stepIndex === contactStep;
            }),
            currentStep: contactStep,
          });
          // Copy contact field value (if present) into the one of the contact a human step
          let step0Contract = $('#form-step-0 select[name=device_contract]').val();
          // May be undefined (no such field) or null (no option selected):
          if (step0Contract) {
            // As of Odoo 12.0 minification removes some spaces in backtick literals
            // hence the use of the + operator and plain old strings below:
            $("#form-step-" + contactStep
              + " select[name=device_contract]").val(step0Contract);
          }
        }
        else {
          setState(wizard, $button, previousState);
          $('.sw-btn-group').show();
        }
      });
  }

  // Let's setup the wizard

  let contactStep = null;
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
    setupHumanContactButton(contactStep);
  }

  $container.smartWizard({
    selected: 0,
    autoAdjustHeight: false,
    keyNavigation: false,
    enableURLhash: false,
    toolbarSettings: {
      toolbarPosition: 'both',
    },
    transition: {
      animation: 'fade',
    },
    theme: 'arrows',
    lang: buttonI18n[$("html").attr("lang").split("-")[0]],
    anchorSettings: {
      removeDoneStepOnNavigateBack: true,
    },
  });

  function _validateFields($parent) {
    let isValid = true;
    $parent.closest(".tab-pane").find('input,select,textarea').each(
      function(idx, elm) {
        isValid = isValid && elm.reportValidity();
      }
    );
    $parent.closest("form").toggleClass("was-validated", !isValid);
    return isValid;
  }

  $container.find("button[type=submit]").click(function() {
    return _validateFields($(this));
  });

  $container.on('leaveStep', function(e, curStep, curIndex, nextIndex, stepDirection) {
    const $elmForm = $('#' + formStepIdPrefix + curIndex);
    if (stepDirection === 'forward' && $elmForm.length) {
      return _validateFields($elmForm);
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
    $container.smartWizard("stepState", [number], enabled ? "enable" : "disable");
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
