odoo.define("account_payment_slimpay.payment_form", (require) => {
    "use strict";

    const checkoutForm = require("payment.checkout_form");
    const manageForm = require("payment.manage_form");

    const slimpayMixin = {
        /**
         * @override
         *
         * In the payment form, we hide payment options to the front-end user,
         * and we select the fitting payment radio option (token or Slimpay form).
         *
         * However, in _displayError, since there's a selected option, the error message is placed
         * next to the payment option, which is consequently hidden.
         *
         * As such, we move the error message out of the payment option element to after the payment option element.
         */
        _displayError: function (title, description = "", error = "") {
            this._super(title, description, error);
            const error_el = $("[name='o_payment_error']");
            if (error_el) {
                const payment_options_el = $("[name='o_payment_option_card']").parent();
                payment_options_el.after(error_el);
            }
        },
    };

    checkoutForm.include(slimpayMixin);
    manageForm.include(slimpayMixin);
});
