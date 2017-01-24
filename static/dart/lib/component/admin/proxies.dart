import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dquery/dquery.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/model/proxy.dart';
import 'package:hgprofiler/component/breadcrumbs.dart';
import 'package:hgprofiler/component/title.dart';
import 'package:hgprofiler/rest_api.dart';

/// A component for viewing and modifying credentials.
@Component(
    selector: 'proxy-list',
    templateUrl: 'packages/hgprofiler/component/admin/proxies.html',
    useShadowDom: false
)
class ProxiesComponent {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('Profiler', '/'),
        new Breadcrumb('Administration', '/admin'),
        new Breadcrumb('Proxies'),
    ];

    List<String> keys;
    Map<int, Proxy> proxies;
    List<String> siteIds;
    String error;
    int loading = 0;
    bool showAddEdit = false;
    bool submittingProxy = false;
    String dialogTitle;
    String dialogClass;
    List<Map> messages = new List<Map>();
    int deleteProxyId;
    int editProxyId;
    String newProxyProtocol;
    String newProxyHost;
    int newProxyPort;
    String newProxyUsername;
    String newProxyPassword;
    bool newProxyActive;
    String proxyError = null;


    final AuthenticationController auth;
    final RestApiController _api;
    final TitleService _ts;
    final Element _element;

    InputElement _inputEl;

    /// Constructor.
    ProxiesComponent(this.auth, this._api, this._element, this._ts) {
        this._fetchProxies();
        this._ts.title = 'Proxies';
    }

    /// Fetch a list of proxies.
    void _fetchProxies() {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/proxies/';

        this._api
            .get(pageUrl, needsAuth: true)
            .then((response) {
                this.proxies = new Map<int, Proxy>();
                response.data['proxies'].forEach((proxy) {
                    this.proxies[proxy['id']] = new Proxy.fromJson(proxy);
                });
                this.keys = new List<String>.from(this.proxies.keys);

            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Show the "add profile" dialog.
    void showAddEditDialog(String mode) {
        if(mode == 'edit') {
            this.dialogTitle = 'Edit Proxy';
            this.dialogClass = 'panel-info';
        } else {
            this.dialogTitle = 'Add Proxy';
            this.dialogClass = 'panel-success';
            this.newProxyProtocol = 'http';
            this.newProxyHost = '';
            this.newProxyPort = 80;
            this.newProxyUsername = null;
            this.newProxyPassword = null;
            this.newProxyActive = true;
        }

        this.showAddEdit = true;
        this.proxyError = null;

        this._inputEl = this._element.querySelector('#proxy-protocol');
        if (this._inputEl != null) {
            // Allow Angular to digest ShowAddEdit before trying to focus. (Can't
            // focus a hidden element.)
            new Timer(new Duration(milliseconds:1), () => this._inputEl.focus());
        }
    }

    /// Hide the "add categories" dialog.
    void hideAddDialog() {
        this.showAddEdit = false;
        this.editProxyId = null;
    }

    void addProxy(Event e, dynamic data, Function resetButton) {
        String pageUrl = '/api/proxies/';
        this.loading++;

        if (this.newProxyUsername == '') {
            this.newProxyUsername = null;
        }

        if (this.newProxyPassword == '') {
            this.newProxyPassword = null;
        }

        Map proxy  = {
            'protocol': this.newProxyProtocol,
            'host': this.newProxyHost,
            'port': this.newProxyPort,
            'username': this.newProxyUsername,
            'password': this.newProxyPassword,
            'active': this.newProxyActive
        };

        Map body = {
            'proxies': [proxy]
        };

        this._api
            .post(pageUrl, body, needsAuth: true)
            .then((response) {
                String msg = 'Added proxy ${this.newProxyHost}://${this.newProxyHost}:${this.newProxyPort}';
                this._showMessage(msg, 'success', 3, true);
                this._fetchProxies();
                this.showAddEdit = false;
            })
            .catchError((response) {
                this.proxyError = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                resetButton();
                this.submittingProxy = false;
            });
    }


    /// Save an edited site.
    void saveProxy(Event e, dynamic data, Function resetButton) {
        String pageUrl = '/api/proxies/${this.editProxyId}';
        this.loading++;
        this.submittingProxy = true;

        if (this.newProxyUsername == '') {
            this.newProxyUsername = null;
        }

        if (this.newProxyPassword == '') {
            this.newProxyPassword = null;
        }

        Map proxy  = {
            'protocol': this.newProxyProtocol,
            'host': this.newProxyHost,
            'port': this.newProxyPort,
            'username': this.newProxyUsername,
            'password': this.newProxyPassword,
            'active': this.newProxyActive
        };

        this._api
            .put(pageUrl, proxy, needsAuth: true)
            .then((response) {
                String uri = '${this.proxies[this.editProxyId].protocol}://';
                uri += '${this.proxies[this.editProxyId].host}:';
                uri += '${this.proxies[this.editProxyId].port}:';
                this.proxies[this.editProxyId] = new Proxy.fromJson(response.data);
                this.showAddEdit = false;
                this._showMessage('Updated proxy ${uri}', 'success', 3, true);
            })
            .catchError((response) {
                String msg = response.data['message'];
                this.proxyError = msg;
            })
            .whenComplete(() {
                this.loading--;
                this.submittingProxy = false;
                resetButton();
            });
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('.add-proxy-form input');
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

    /// Set proxy for deletion and show confirmation modal
    void setDeleteId(int id_) {
        this.deleteProxyId = id_;
        String selector = '#confirm-delete-modal';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).show();
    }

    /// Set proxy to be edited and show add/edit dialog.
    void editProxy(int id_) {
        this.newProxyProtocol = this.proxies[id_].protocol;
        this.newProxyHost = this.proxies[id_].host;
        this.newProxyPort = this.proxies[id_].port;
        this.newProxyUsername = this.proxies[id_].username;
        this.newProxyPassword = this.proxies[id_].password;
        this.newProxyActive = this.proxies[id_].active;
        this.editProxyId = id_;
        this.showAddEditDialog('edit');
    }

    /// Delete proxy specified by deleteProxyId.
    void deleteProxy(Event e, dynamic data, Function resetButton) {
        if(this.deleteProxyId == null) {
            return;
        }
        String pageUrl = '/api/proxies/${this.deleteProxyId}';
        String uri = '${this.proxies[this.deleteProxyId].protocol}://';
        uri += '${this.proxies[this.deleteProxyId].host}:';
        uri += '${this.proxies[this.deleteProxyId].port}:';
        this.loading++;

        this._api
            .delete(pageUrl, needsAuth: true)
            .then((response) {
                this._showMessage('Deleted proxy ${uri}', 'success', 3, true);
                this.proxies.remove(deleteProxyId);
                this.keys.remove(deleteProxyId);
                this.deleteProxyId = null;
            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {
                this.loading--;
                resetButton();
                Modal.wire($("#confirm-delete-modal")).hide();
            });
    }

    /// Listen for proxy updates.
    void _proxyListener(Event e) {
        Map json = JSON.decode(e.data);

        if (json['error'] == null) {
            Proxy proxy = new Proxy.fromJson(json["proxy"]);
            String uri = '${proxy.protocol}://';
            uri += '${proxy.host}:';
            uri += '${proxy.port}:';
            if (json['status'] == 'created') {
                this._showMessage('Proxy "${json["name"]}" created.', 'success', 3);
                this.proxies[proxy.id] = proxy;
                this.keys.add(proxy.id);
            }
            else if (json['status'] == 'updated') {
                this._showMessage('Category "${json["name"]}" updated.', 'info', 3);
                this.proxies[proxy.id] = proxy;
            }
            else if (json['status'] == 'deleted') {
                this._showMessage('Category "${json["name"]}" deleted.', 'danger', 3);
                this.proxies.remove(proxy);
                this.keys.remove(proxy.id);
            }
        }
    }
}
