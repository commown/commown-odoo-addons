/* global module */

module.exports = {
    env: {
        browser: true,
        es6: true,
    },
    globals: {
        Atomics: "readonly",
        SharedArrayBuffer: "readonly",
    },
    parserOptions: {
        ecmaVersion: 2018,
    },
    rules: {
        "space-before-function-paren": "off",
        "prefer-arrow-callback": "off",
        "prefer-template": "off",
        "func-names": "off",
        "no-empty-function": "off",
    },
};
