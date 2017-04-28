import 'dart:html';
import 'dart:convert';

import 'package:angular/angular.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/sse.dart';
import 'package:hgprofiler/model/user.dart';

/// The top navigation bar.
@Component(
    selector: 'nav',
    templateUrl: 'packages/hgprofiler/component/nav.html',
    useShadowDom: false
)
class NavComponent {
    AuthenticationController auth;
    bool showDevFeatures = false;

    String _secretWord = 'DEVMODE';
    int _index = 0;

    final SseController _sse;
    final RouteProvider _rp;
    /// Constructor.
    NavComponent(this.auth, this._sse, this._rp) {
        if (window.localStorage['devmode'] != null) {
            showDevFeatures = window.localStorage['devmode'] == 'true';
        } else {
            window.localStorage['devmode'] = this.showDevFeatures ? 'true' : 'false';
        }

        // Show development features when user types "DEVMODE".
        document.body.onKeyPress.listen((e) {
            String typedLetter;

            try {
                typedLetter = new String.fromCharCodes([e.charCode]);
            } catch (RangeError) {
                this._index = 0;
                return;
            }

            if (this._secretWord[this._index] == typedLetter) {
                this._index++;

                if (this._index == _secretWord.length) {
                    this.showDevFeatures = !this.showDevFeatures;
                    window.localStorage['devmode'] = this.showDevFeatures ? 'true' : 'false';
                    this._index = 0;
                }
            } else {
                this._index = 0;
            }
        });

        // Add event listeners...
        this._sse.onUser.listen(this._userListener);
    }

    // User SSE event listener
    void _userListener(Event e) {
        Map user_data = JSON.decode(e.data);
        User user = new User.fromJson(user_data);
        if (user.id == this.auth.currentUser.id) {
            // Update current user credits
            this.auth.currentUser.credits = user.credits;
        }
    }
}
