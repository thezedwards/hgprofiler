import json
import math
import stripe

from flask import g, jsonify, request
from flask.ext.classy import FlaskView, route
from werkzeug.exceptions import (BadRequest, Conflict, Forbidden,
                                 NotFound, ServiceUnavailable)

from app.authorization import login_required
from app.rest import validate_request_json
from model import Configuration, Site, User
from model.configuration import get_config

_payment_attrs = {
    'user_id': {'type': int, 'required': True},
    'amount': {'type': int, 'required': True},
    'stripe_token': {'type': str, 'required': True},
    'description': {'type': str, 'required': True},
    'currency': {'type': str, 'required': True},
}


def cost(units, cost_per_unit):
    """
    Calculate cost with discount.
    """
    #rate = math.pow(0.967,(units/100))
    cost = cost_per_unit * math.pow(units, 0.95) + 150
    return cost


class CheckoutView(FlaskView):
    """
    API for managing user payments.
    """
    decorators = [login_required]

    def index(self):
        '''
        Retrieve checkout configuration.

        **Example Response**

        .. sourcecode:: json

            {
                "credit_cost":  0.9,
                "currency": "usd",
                "total_sites": 117,
                "cost_all_sites": 127.5,
                "stripe_public_key": "pk_123456789",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>json int cost: cost of credit (in lowest denomination, e.g. cents)
        :>json str currency: currency code
        :>json int total_sites: total number of available sites to search
        :>json float cost_all_sites: cost of searching all sites
        :>json stripe_public_key: the public Stripe API key

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        '''
        costs = {}
        key = 'credit_cost'
        cost_conf = g.db.query(Configuration) \
                               .filter(Configuration.key==key) \
                               .first()

        if cost_conf is None:
            raise NotFound('There is no configuration item named "{}".'.format(key))

        # Generate price list
        for i in range(100, 100100, 100):
            costs[i] = cost(i, float(cost_conf.value))

        key = 'credit_currency'
        currency_conf = g.db.query(Configuration) \
                         .filter(Configuration.key==key) \
                         .first()

        if currency_conf is None:
            raise NotFound('There is no configuration item named "{}".'.format(key))

        key = 'stripe_public_key'
        stripe_key_conf = g.db.query(Configuration) \
                         .filter(Configuration.key==key) \
                         .first()

        if stripe_key_conf is None:
            raise NotFound('There is no configuration item named "{}".'.format(key))
        total_sites = g.db.query(Site).filter(Site.valid==True).count()

        data = {
            'costs': costs,
            'cost_per_credit': float(cost_conf.value),
            'currency': currency_conf.value,
            'total_sites': total_sites,
            'cost_all_sites': float(total_sites) * float(cost_conf.value),
            'stripe_public_key': stripe_key_conf.value
        }
        return jsonify(data)


    def post(self):
        '''
        Process user payment.

        **Example Request**

        .. sourcecode:: json

            {
                "user_id": 1,
                "stripe_token": "tok_1A9VDuL25MRJTn0APWrFQrN6",
                "amount": 20.00,
                "currency": "usd",
                "description": "200 credits for $20",
            }

        **Example Response**

        .. sourcecode:: json

            {
                "message": "1 site created."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :<json int user_id: the user ID
        :<json str stripe_token: the stripe payment token
        :<json int credits: the purchase credits
        :<json float amount: the purchase amount

        :>header Content-Type: application/json
        :>json string message: API response message

        :status 200: ok
        :status 400: invalid request body
        :status 401: authentication required
        :status 403: not authorized to make the requested changes
        '''
        # Validate json input
        request_json = request.get_json()
        validate_request_json(request_json, _payment_attrs)

        user = g.db.query(User).filter(User.id == request_json['user_id']).first()

        if g.user.id != user.id:
            raise Forbidden('You may only purchase credits for '
                            'your own account.')

        # Configure stripe client
        try:
            stripe.api_key = get_config(session=g.db,
                             key='stripe_secret_key',
                             required=True).value
        except Exception as e:
            raise ServiceUnavailable(e)


        # Stripe token is created client-side using Stripe.js
        token = request_json['stripe_token']

        # Get payment paremeters
        amount = request_json['amount']
        description = request_json['description']
        currency = request_json['currency']

        try:
            # Charge the user's card:
            charge = stripe.Charge.create(
                  amount=amount,
                  currency=currency,
                  description=description,
                  source=token,
            )
        except stripe.error.CardError as e:
          # Since it's a decline, stripe.error.CardError will be caught
          body = e.json_body
          err  = body['error']
          raise BadRequest('Card error: {}'.format(err['message']))
        except stripe.error.RateLimitError as e:
          # Too many requests made to the API too quickly
          body = e.json_body
          err  = body['error']
          raise BadRequest('Rate limit error: {}'.format(err['message']))
        except stripe.error.InvalidRequestError as e:
          # Invalid parameters were supplied to Stripe's API
          body = e.json_body
          err  = body['error']
          raise BadRequest('Invalid parameters: {}'.format(err['message']))
        except stripe.error.AuthenticationError as e:
          # Authentication with Stripe's API failed
          # (maybe API keys changed recently)
          body = e.json_body
          err  = body['error']
          raise ServiceUnavailable('Stripe authentication error: {}'.format(err['message']))
        except stripe.error.APIConnectionError as e:
          # Network communication with Stripe failed
          body = e.json_body
          err  = body['error']
          raise ServiceUnavailable('Stripe API communication failed: {}'.format(err['message']))
        except stripe.error.StripeError as e:
          # Generic error
          body = e.json_body
          err  = body['error']
          raise ServiceUnavailable('Stripe error: {}'.format(err['message']))
        except Exception as e:
          # Something else happened, completely unrelated to Stripe
          raise ServiceUnavailable('Error: {}'.format(e))

        user.credits += int(amount)
        g.db.commit()
        g.redis.publish('user', json.dumps(user.as_dict()))

        message = '{} credits added.'.format(amount)
        response = jsonify(message=message)
        response.status_code = 202

        return response
