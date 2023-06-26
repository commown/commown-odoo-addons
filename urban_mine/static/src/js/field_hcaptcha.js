odoo.define('urban_mine.hcaptcha', function (require) {
  "use strict";

  var snippet_animation = require('website.content.snippets.animation');
  var form_builder_send = snippet_animation.registry.form_builder_send;
  form_builder_send.prototype.recaptcha_js_url = "https://js.hcaptcha.com/1/api.js";

});
