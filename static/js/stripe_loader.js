/*
 * Functions for loading Stripe elements
*  https://stripe.com/docs/elements
*/

// Global stripe objects
var stripe = null;
var elements = null;
var cardElement = null;

// Custom styling can be passed to options when creating an Element.
var style = {
    base: {
        // Add your base input styles here. For example:
        fontSize: '16px',
        lineHeight: '24px'
    }
};

/**
 * Mount Stripe card elements, validate input, and pass Stripe token to
 * callback.
 *
 * @param {string} publicKey - The public Stripe API key
 **/
function loadStripe(publicKey) {
    /*
    Two functions are imported from Dart (using Dart js interop):

    1. setState(state, [errorMsg]) - for setting button states and
                                     displaying error messages
    2. stripeTokenHandler(token) - token handler callback
    */
    stripe = Stripe(publicKey);
    elements = stripe.elements();

    // Create an instance of the card Element
    cardElement = elements.create('card', {style: style});

    // Add an instance of the card Element into the `card-element` <div>
    cardElement.mount('#card-element');
    cardElement.addEventListener('change', function(event) {
        if (event.error) {
            setState('error', event.error.message);
        } else {
            setState('default');
        }
    });

    // Create a token or display an error the form is submitted.
    var form = document.getElementById('payment-form');
    var inputs = form.getElementsByTagName('input');
    form.addEventListener('submit', function(event) {
        event.preventDefault();

        stripe.createToken(cardElement).then(function(result) {
            if (result.error) {
                // Inform the user if there was an error
                setState('error', result.error.message);
            } else {
                // Pass token to callback.
                stripeTokenHandler(result.token);
                setState('processing');
            }
        });
    });
};

/// Unload Stripe objects.
function unloadStripe() {
    try {
        cardElement.unmount();
        stripe = null;
        elements = null;
        cardElement = null;
    }
    catch(err) {
        console.log('Error unloading Stripe: ' + err);
    }
};
