import 'dart:async';
import 'dart:html';
import 'dart:convert';
import 'dart:math' as math;

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dquery/dquery.dart';
import 'package:intl/intl.dart';
import 'package:observe/observe.dart';
import 'package:observe/mirrors_used.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/query_watcher.dart';
import 'package:hgprofiler/component/breadcrumbs.dart';
import 'package:hgprofiler/component/title.dart';
import 'package:hgprofiler/model/user.dart';
import 'package:hgprofiler/rest_api.dart';
import 'package:hgprofiler/sse.dart';

/// A component for viewing and modifying sites.
@Component(
    selector: 'user-credit',
    templateUrl: 'packages/hgprofiler/component/user/credit_view.html',
    useShadowDom: false
)
class UserCreditComponent {

    AuthenticationController auth;
    bool canEdit = false;
    num creditCost;
    Map<int,num> costs;
    num creditCostAll;
    String stripePublicKey;
    int minCredits = 400;
    num totalSearches;
    int totalSites;
    String displayName;
    final Element _element;
    List<Breadcrumb> crumbs;
    int id;
    int loading = 0;
    List<Map> messages = new List<Map>();
    User user;

    InputElement _inputEl;
    QueryWatcher _queryWatcher;

    final RestApiController api;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    ObservableBox credits;
    num dollarAmount;
    int centAmount;

    /// Constructor.
    UserCreditComponent(this.auth, this.api, this._element, this._rp, this._sse, this._ts) {
        String idParam = Uri.decodeComponent(this._rp.parameters['id']);
        this.credits = new ObservableBox(this.minCredits);
        this.id = int.parse(idParam, radix:10);
        this.canEdit = this.auth.isAdmin() || this.id == this.auth.currentUser.id;
        this._ts.title = 'Credit';
        this.crumbs = [
            new Breadcrumb('Profiler', '/'),
            new Breadcrumb('User Directory', '/user'),
            new Breadcrumb('Credit', '/credit'),
        ];

        RouteHandle rh = this._rp.route.newHandle();

        // Add event listeners...
        UnsubOnRouteLeave(rh, [
            this.credits.changes.listen(this._creditsListener),
            this._sse.onUser.listen(this._userListener)
        ]);

        this._fetchUser();
        //this._fetchCheckoutConf().then((_) => this.dollarAmount = this._costCalculator(this.credits.value) / 100)
        //                         .then((_) => this.centAmount = this._costCalculator(this.credits.value))
        //                         .then((_) => this.totalSearches = (this.credits.value / this.totalSites).floor());
        this._fetchCheckoutConf().then((_) {
                                    if(this.credits.value == 0) {
                                        this.dollarAmount = 0;
                                    } else {
                                        this.dollarAmount = this._costCalculator(this.credits.value) / 100;
                                    }
                                 })
                                 .then((_) => this.centAmount = this._costCalculator(this.credits.value))
                                 .then((_) {
                                     if(this.credits.value == 0 || this.totalSites == 0) {
                                         this.totalSearches = 0;
                                     } else {
                                         this.totalSearches = (this.credits.value / this.totalSites).floor();
                                    }
                                 });
    }

    /// Calculate dollar cost
    String dollarCost(double centCost) {
        if (centCost == null) {
            return 'N/A';
        }
        return (centCost/100).toStringAsFixed(2);
    }

    /// Format credit value
    String friendlyNumber(int credits) {
        if (credits == null) {
            return 'N/A';
        }
        var f = new NumberFormat("#,###,###", "en_US");
        return f.format(credits);
    }

    /// Trigger add site when the user presses enter in the site input.
    void _creditsListener(Event e) {
        this.centAmount = this._costCalculator(this.credits.value);

        if(this.credits.value == 0) {
            this.dollarAmount = 0;
        } else {
            this.dollarAmount = this._costCalculator(this.credits.value) / 100;
        }

         if(this.totalSites == 0) {
             this.totalSearches = 0;
         } else {
             this.totalSearches = (this.credits.value / this.totalSites).floor();
        }
    }

    int _costCalculator(num credits) {
        int cost;
        cost = credits * this.creditCost;
        return cost;
    }

    // Fetch cost of credits.
    Future _fetchCheckoutConf() {
        Completer completer = new Completer();
        this.costs = new Map<int, num>();
        this.loading++;

        this.api
            .get('/api/checkout/', needsAuth: true)
            .then((response) {
                this.creditCost = response.data['cost_per_credit'];
                this.creditCostAll = response.data['cost_all_sites'];
                this.totalSites = response.data['total_sites'];
                this.stripePublicKey = response.data['stripe_public_key'];
                response.data['costs'].forEach((key, value) {
                    this.costs[int.parse(key)] = value;
                });
            })
            .catchError((response) {
                this._showMessage(response.data['message'], 'danger');
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch data about this user.
    Future _fetchUser() {
        Completer completer = new Completer();
        this.loading++;

        this.api
            .get('/api/users/${this.id}', needsAuth: true)
            .then((response) {
                this.user = new User.fromJson(response.data);

                displayName = this.user.name != null
                            ? this.user.name
                            : this.user.email;

                this.crumbs[this.crumbs.length-1] = new Breadcrumb(displayName);
                this._ts.title = displayName;
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }


    /// Show a notification to the user
    void _showMessage(String text,
                      String type,
                      [int seconds = 3, bool icon]) {

        Map message = {
            'text': text,
            'type': type,
            'icon': icon
        };
        this.messages.add(message);
        if (seconds > 0) {
            new Timer(new Duration(seconds:seconds), () => this.messages.remove(message));
        }
    }

    // User SSE event listener
    void _userListener(Event e) {
        Map user_data = JSON.decode(e.data);
        User user = new User.fromJson(user_data);
        if (user.id == this.user.id) {
            // Update user
            DivElement currentCredits = querySelector('#current-credits');
            if (this.user.credits > user.credits) {
                currentCredits.setAttribute('class', 'current-value-down shake shake-constant');
            } else if (this.user.credits < user.credits) {
                currentCredits.setAttribute('class', 'current-value-up shake shake-constant');

            }
            this.user = user;

            new Timer(new Duration(seconds:2), () {
                currentCredits.setAttribute('class', 'current-value');
            });
        }
    }
}
