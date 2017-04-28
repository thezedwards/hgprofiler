import 'dart:async';
import 'dart:convert';
import 'dart:html';
import 'dart:js';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/rest_api.dart';


/// A form for Stripe checkout.
@Component(
    selector: 'stripe-form',
    templateUrl: 'packages/hgprofiler/component/stripe_form.html',
    useShadowDom: false)
class StripeFormComponent {
    @NgAttr('data-amount')
    double amount;

    @NgAttr('data-dollar-amount')
    double dollarAmount;

    @NgAttr('data-currency')
    String currency = 'usd';

    @NgAttr('data-key')
    String key;

    @NgAttr('data-name')
    String name = 'Stripe Checkout';

    @NgAttr('data-description')
    String description = 'Pay with card';

    @NgAttr('data-user-id')
    int userId;

    String error;
    bool loading = false;
    bool complete = false;
    String stripePublicKey = 'pk_test_4XxInS26VHCH0cXvlrYX58W5';
    bool submitted = false;
    String xauthToken;

    final AuthenticationController _auth;
    final RestApiController _api;

    //StripeFormComponent(this._element);
    StripeFormComponent(this._auth, this._api) {
        this.xauthToken = this._auth.token;
        context['stripeTokenHandler'] = allowInterop(stripeTokenHandler);
        context['setState'] = allowInterop(setState);
    }

    /// Set payment button class and text
    void setState(state, [String errorMsg]) {
        ButtonElement payButton = querySelector('#pay-button');
        Element payIcon = querySelector('#pay-icon');
        DivElement stripeErrors = querySelector('#stripe-errors');
        if (state == 'processing') {
            payButton.disabled = true;
            payButton.innerHtml = '<i class="fa fa-spinner fa-spin"></i> Processing';
            stripeErrors.innerHtml = '';
            stripeErrors.setAttribute('class', '');
            stripeErrors.setAttribute('role', '');
        } else if (state == 'complete') {
            payButton.setAttribute('class', 'btn btn-success');
            payButton.innerHtml = '<i class="fa fa-check-square-o"></i> Complete';
            stripeErrors.innerHtml = '';
            stripeErrors.setAttribute('class', '');
            stripeErrors.setAttribute('role', '');
        } else if (state == 'error') {
            payButton.disabled = true;
            payButton.innerHtml = 'Pay <i class="fa fa-usd"></i>${dollarAmount}';
            stripeErrors.setAttribute('class', 'alert alert-danger');
            stripeErrors.setAttribute('role', 'alert');
            stripeErrors.innerHtml = '${errorMsg}';
        } else {
            payButton.disabled = false;
            payButton.setAttribute('class', 'btn btn-info');
            payButton.innerHtml = 'Pay <i class="fa fa-usd"></i>${dollarAmount}';
            stripeErrors.innerHtml = '';
            stripeErrors.setAttribute('class', 'default');
            stripeErrors.setAttribute('role', '');
        }
    }

    void payButtonClickHandler() {
        String selector = '#stripe';
        this.complete = false;
        DivElement modalDiv = querySelector(selector);
        Modal.wire(modalDiv).show();
        this.setState('default');
        context.callMethod('loadStripe', [this.key]);
    }

    /// Fetch Stripe Public Key from configuration
    Future _fetchAPIKey() {
        Completer completer = new Completer();
        this.loading = true;
        String paymentUrl = '/api/users/${userId}/payment';

    }

    /// Submit a user payment request to API.
    Future _paymentRequest(String tokenId) {
        Completer completer = new Completer();
        this.loading = true;
        //String paymentUrl = '/api/users/${userId}/payment';
        String paymentUrl = '/api/checkout/';
        Map body = {
            'user_id': this.userId,
            'stripe_token': tokenId,
            'amount': num.parse(this.amount).toInt(),
            'description': this.description,
            'currency': this.currency
        };
        this._api
            .post(paymentUrl, body, needsAuth: true)
            .then((response) {
                this.loading = false;
                this.complete = true;
                // Change button state to show completed transaction.
                new Timer(new Duration(seconds:0.1), () {
                    ButtonElement payButton = querySelector('#pay-button');
                    payButton.innerHtml = '<i class="fa fa-lg fa-check-square-o"></i> Complete';
                    payButton.setAttribute('class', 'btn btn-success');
                });
                // Close the modal.
                new Timer(new Duration(seconds:1), () {
                    String selector = '#stripe';
                    DivElement modalDiv = querySelector(selector);
                    Modal.wire(modalDiv).hide();
                });
            })
            .catchError((response) {
                this.setState('error', response.data['message']);
            });
        completer.complete();
        return completer.future;
    }

    void stripeTokenHandler(token) {
        this.error = null;
        this.complete = false;
        Map tokenData = JSON.decode(
                    context['JSON'].callMethod(
                        'stringify',
                        [token])
                    );
        this._paymentRequest(tokenData['id']);
    }
}
