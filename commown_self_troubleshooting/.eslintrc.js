module.exports = {
  env: {
    browser: true,
    es6: true,
  },
  extends: [
    'airbnb-base',
  ],
  globals: {
    Atomics: 'readonly',
    SharedArrayBuffer: 'readonly',
  },
  parserOptions: {
    ecmaVersion: 2018,
  },
  rules: {
    'space-before-function-paren': 'off',
    'prefer-arrow-callback': 'off',
    'prefer-template': 'off',
    'func-names': 'off',
  },
};
