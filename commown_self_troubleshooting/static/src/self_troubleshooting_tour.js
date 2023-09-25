odoo.define("commown_self_troubleshooting.tour_fp2_battery", function(require) {
  "use strict";

  var tour = require("web_tour.tour");

  // Helpers

  let humanText = "Contacter un humain";
  const visiblePane = "#smartwizard .tab-pane:visible";
  const visibleDeviceContract = visiblePane + " select[name=device_contract]"
  const visibleMoreInfo = visiblePane + " textarea[name=more_info]";
  const inStep0 = "h2:contains('Appareil concerné')";
  const notInStep0 = "h2:not(:contains('Appareil concerné'))";

  const _submitForm = {
    content: "Submit the form",
    trigger: visiblePane + " button[type=submit]",
  };

  const commonSteps = {

    // Constant steps

    gotoNextStep: {
      content: "Go to next wizard step",
      trigger: "button.sw-btn-next",
    },

    fillInContract: {
      content: "Select a contract in the dedicated drop down",
      extra_trigger: inStep0,
      trigger: visibleDeviceContract,
      run: "text SO",
    },

    submitForm: _submitForm,

    // Function that return an array of steps

    funcAddMoreInfo: function(text) {
      return [{
        content: "Add more info",
        trigger: visibleMoreInfo,
        // Automatic action does not support '\n' in the content, so do it ourselves:
        run: function() {this.$anchor.val(text)},
      }];
    },

    funcCreateAndCheckTicket: function(text, moreInfo) {
      let result = [_submitForm];
      if (text) {
        result.push({
          content: "Check created ticket: std message",
          trigger: "p:contains('" + text + "')",
        });
      }
      if (moreInfo) {
        result.push({
          content: "Check created ticket: customer message",
          trigger: "pre:contains('" + moreInfo + "')",
        });
      }
      return result;
    },
  };

  // Actual tests

  tour.register(
    "commown_self_troubleshooting_tour_fp2_battery_inf_80",
    { url: "/my" },
    [
      {
        content: "Go to FP2 display troubleshooting page",
        trigger: 'a[href="/page/self-troubleshoot-fp2-battery"]',
      },
      commonSteps.fillInContract,
      commonSteps.gotoNextStep,
      {
        content: "Step 0 is now marked done",
        trigger: "#smartwizard a.nav-link:eq(0).done",
        run: function() {},
      },
      {
        content: "Select battery capacity less than the limit",
        trigger: "select[id=accu_battery]",
        run: "text Inférieure à 80%",
      },
      {
        content: "Check step 2 nav link is disabled",
        trigger: "#smartwizard a.nav-link:eq(2).disabled",
        run: function() {},
      },
      {
        content: "Check step 3 nav link is not disabled",
        trigger: "#smartwizard a.nav-link:eq(3):not(.disabled)",
        run: function() {},
      },
      commonSteps.gotoNextStep,
      {
        content: "Check name",
        trigger: "input[name=name]",
        run: function() {
          const user = $("#top_menu li:last-child a b span:eq(0)").text();
          if (this.$anchor.val() !== user) {
            console.log("Field 'name' value should equal the logged-in user name:")
            console.log("Got: '" + this.$anchor.val() + "' instead of '" + user + "'.");
            console.log("Error (see above)");
          }
        },
      },
      commonSteps.gotoNextStep,
      ...commonSteps.funcAddMoreInfo("Hello!\nAre you OK?"),
      ...commonSteps.funcCreateAndCheckTicket(
        "la batterie de mon FP2 doit être changée",
        "Hello!\nAre you OK?"
      ),
    ]
  );

  tour.register(
    "commown_self_troubleshooting_tour_fp2_battery_sup_80",
    { url: "/my" },
    [
      {
        content: "Go to FP2 display troubleshooting page",
        trigger: 'a[href="/page/self-troubleshoot-fp2-battery"]',
      },
      commonSteps.fillInContract,
      commonSteps.gotoNextStep,
      {
        content: "Select battery capacity less than the limit",
        trigger: "select[id=accu_battery]",
        run: "text Supérieure à 80%",
      },
      {
        content: "Check step 2 nav link is not disabled",
        trigger: "#smartwizard a.nav-link:eq(2):not(.disabled)",
        run: function() {},
      },
      {
        content: "Check step 3 nav link is disabled",
        trigger: "#smartwizard a.nav-link:eq(3).disabled",
        run: function() {},
      },
      commonSteps.gotoNextStep,
      ...commonSteps.funcAddMoreInfo("text FB drains the battery!"),
      ...commonSteps.funcCreateAndCheckTicket(
        "je vais effectuer le test en mode sans échec",
        "FB drains the battery"
      ),
    ]
  );

  tour.register(
    "commown_self_troubleshooting_tour_fp2_battery_contact_human",
    { url: "/my" },
    [
      {
        content: "Go to FP2 display troubleshooting page",
        trigger: 'a[href="/page/self-troubleshoot-fp2-battery"]',
      },
      {
        content: "Click on the 'contact a human' button",
        trigger: `#contactAHuman:contains('${humanText}')`,
      },
      {
        content: "All steps but 'Contact a human' are disabled",
        extra_trigger: notInStep0,
        // As of Odoo 12.0 minification removes some spaces in backtick literals
        // hence the use of the + operator and plain old strings below:
        trigger: "#smartwizard .nav-item:contains('" + humanText +"') a:not(.disabled)",
        run: function() {
          let hasError = false;
          $(`#smartwizard .nav-item:not(:contains('${humanText}'))`).each(
            function(idx, $elm) {
              if ($("a.disabled", $elm).length === 0) {
                console.log("***** Nav item n°" + idx + " should be disabled! *****");
                hasError = true;
              }
            }
          );
          if (hasError) { console.log("Error (see above)"); }
        },
      },
      {
        content: "Contract field is a copy of first step's: empty for now",
        extra_trigger: notInStep0,
        trigger: visibleDeviceContract,
        run: function() {
          if (this.$anchor.val()) {
            console.log("***** Device contract should be empty *****")
            console.log("Error (see above)");
          }
        },
      },
      {
        content: "Button text has changed - click on it",
        trigger: "#contactAHuman:contains('Revenir')",
      },
      commonSteps.fillInContract,
      {
        content: "The button returned to its original text. Click it again.",
        trigger: `#contactAHuman:contains('${humanText}')`,
      },
      {
        content: "Contract field is a copy of first step's: SOxxx",
        extra_trigger: notInStep0,
        trigger: visibleDeviceContract,
        run: function() {
          if (! this.$anchor.val()) {
            console.log("A contract should have been automatically selected!");
            console.log("Error (see above)");
          }
        },
      },
      ...commonSteps.funcAddMoreInfo("Please call me!\nQuick!"),
      ...commonSteps.funcCreateAndCheckTicket(
        "nformations complémentaires",
        "Please call me!\nQuick!"
      ),
    ]
  );

  tour.register(
    "commown_self_troubleshooting_tour_termination_no_commitment",
    { url: "/my" },
    [
      {
        content: "Go to Contract termination page",
        trigger: 'a[href="/page/self-troubleshoot-contract-termination"]',
      },
      commonSteps.fillInContract,
      commonSteps.gotoNextStep,
      ...commonSteps.funcAddMoreInfo("Goodbye!"),
      ...commonSteps.funcCreateAndCheckTicket("Je souhaite résilier", "Goodbye!"),
    ]
  );

  tour.register(
    "commown_self_troubleshooting_tour_termination_commitment_transfer",
    { url: "/my" },
    [
      {
        content: "Go to Contract termination page",
        trigger: 'a[href="/page/self-troubleshoot-contract-termination"]',
      },
      commonSteps.fillInContract,
      commonSteps.gotoNextStep,
      {
        "content": "Check step title",
        "trigger": "#contract_termination",
        "extra_trigger": visiblePane + " h2:contains('Je suis toujours engagé')",
        "run": "text Transférer mon contrat",
      },
      commonSteps.gotoNextStep,
      {
        content: "Check active step",
        trigger: ".nav-link.active:contains('Transfert de contrat')",
        run: function() {},
      },
      ...commonSteps.funcAddMoreInfo("Found some!"),
      ...commonSteps.funcCreateAndCheckTicket(
        "Je souhaite effectuer un transfert de contrat.",
        "Found some!"
      ),
    ]
  );

  tour.register(
    "commown_self_troubleshooting_tour_termination_commitment_pay",
    { url: "/my" },
    [
      {
        content: "Go to Contract termination page",
        trigger: 'a[href="/page/self-troubleshoot-contract-termination"]',
      },
      commonSteps.fillInContract,
      commonSteps.gotoNextStep,
      {
        "content": "Check step title",
        "trigger": "#contract_termination",
        "extra_trigger": visiblePane + " h2:contains('Je suis toujours engagé')",
        "run": "text Régler",
      },
      commonSteps.gotoNextStep,
      {
        content: "Check active step",
        trigger: ".nav-link.active:contains('Régler')",
        run: function() {},
      },
      ...commonSteps.funcCreateAndCheckTicket(
        "Je souhaite régler la totalité de mes loyers.",
      ),
    ]
  );

});
