$(function() {

    function toggleValueMatchClass(widget) {
        // Toggle the "attribute-value-match" css class on all elements of
        // the page that match the js-attribute-dependant and the
        // js-attribute-[product_id]-[attribute_id] selectors corresponding
        // to the attribute selected in passed widget argument.
        var matchCssName = 'js-' + widget.name + '-' + widget.value;
        $('.js-attribute-dependant').each(function() {
            $(this).toggleClass('attribute-value-match',
                                $(this).hasClass(matchCssName));
        });
    }

    $('.oe_website_sale').each(function() {

        var oe_website_sale = this;

        console.debug('Setting up automatic css change on variant choice');

        var widgetSelector = 'input.js_variant_change,select.js_variant_change';

        $(widgetSelector, oe_website_sale).each(function(index, el) {
            toggleValueMatchClass(el);
        });
        $(oe_website_sale).on('change', widgetSelector, function (ev) {
            toggleValueMatchClass(ev.target);
        });

    });

});
