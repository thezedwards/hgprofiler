import 'dart:html';

import 'package:angular/angular.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/rest_api.dart';

/// Handles server-sent events.
@Injectable()
class SseController {

    Stream<Event> onArchive;
    Stream<Event> onCategory;
    Stream<Event> onResult;
    Stream<Event> onSite;
    Stream<Event> onWorker;
    Stream<Event> onUser;

    AuthenticationController _auth;
    EventSource _eventSource;
    RestApiController _api;

    /// Constructor
    SseController(this._api, this._auth) {
        String url = this._api.authorizeUrl('/api/notification/');
        url += '&client-id=${this._auth.clientId}';
        this._eventSource = new EventSource(url);

        this._eventSource.onError.listen((Event e) {
            window.console.log('Error connecting to SSE!');
        });

        // Set up event streams.
        this.onArchive = this._eventSource.on['archive'];
        this.onCategory = this._eventSource.on['category'];
        this.onResult = this._eventSource.on['result'];
        this.onSite = this._eventSource.on['site'];
        this.onWorker = this._eventSource.on['worker'];
        this.onUser = this._eventSource.on['user'];
    }
}

/// A helper that unsubscribes a list of subscriptions when leaving a route.
///
/// This saves a lot of boilerplate code in each controller.
void UnsubOnRouteLeave(RouteHandle rh, List<StreamSubscription> listeners) {
    rh.onLeave.take(1).listen((e) {
        listeners.forEach((listener) => listener.cancel());
    });
}
