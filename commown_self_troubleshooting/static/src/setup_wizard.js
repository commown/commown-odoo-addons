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
