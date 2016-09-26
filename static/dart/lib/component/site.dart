import 'dart:async';
import 'dart:html';
import 'dart:convert';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dquery/dquery.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/query_watcher.dart';
import 'package:hgprofiler/component/breadcrumbs.dart';
import 'package:hgprofiler/component/pager.dart';
import 'package:hgprofiler/model/result.dart';
import 'package:hgprofiler/component/title.dart';
import 'package:hgprofiler/model/site.dart';
import 'package:hgprofiler/rest_api.dart';
import 'package:hgprofiler/sse.dart';

/// A component for viewing and modifying sites.
@Component(
    selector: 'site',
    templateUrl: 'packages/hgprofiler/component/site.html',
    useShadowDom: false
)
class SiteComponent extends Object
                    implements ShadowRootAware {

    String siteError;
    List<Breadcrumb> crumbs = [
        new Breadcrumb('Profiler', '/'),
        new Breadcrumb('Sites', '/site'),
    ];
    int deleteSiteId;
    String dialogTitle;
    String dialogClass;
    int editSiteId;
    final Element _element;
    List<String> keys;
    int loading = 0;
    List<Map> messages = new List<Map>();
    String newSiteName;
    String newSiteCategory;
    String newSiteCategoryDescription = 'Select a category';
    String newSiteUrl;
    String newSiteSearchText;
    int newSiteStatusCode;
    Pager pager;
    Result result;
    String query;
    Map<String,Function> sites;
    List<String> siteCategories;
    List<String> siteIds;
    bool showAdd = false;
    bool submittingSite = false;
    String testError;
    int testSiteId;
    bool testing = false;
    String trackerId;

    InputElement _inputEl;
    Router _router;
    QueryWatcher _queryWatcher;

    final AuthenticationController _auth;
    final RestApiController api;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    SiteComponent(this._auth, this.api, this._element, this._router, this._rp, this._sse, this._ts) {
        this._ts.title = 'Sites';

        RouteHandle rh = this._rp.route.newHandle();
        this._queryWatcher = new QueryWatcher(
            rh,
            ['page', 'rpp'],
            this._fetchCurrentPage
        );

        // Add event listeners...
        UnsubOnRouteLeave(rh, [
            this._sse.onSite.listen(this._siteListener),
	    this._sse.onResult.listen(this._resultListener),
        ]);

        this._fetchCategories();
        this._fetchCurrentPage();
    }

    /// Show the "add profile" dialog.
    void showAddDialog(string mode) {
        if(mode == 'edit') {
            this.dialogTitle = 'Edit Site';
            this.dialogClass = 'panel-info';
        } else {
            this.dialogTitle = 'Add Site';
            this.dialogClass = 'panel-success';
            this.newSiteName = null;
            this.newSiteCategory = null;
            this.newSiteStatusCode = null;
            this.newSiteSearchText = null;
            this.newSiteCategoryDescription = 'Select a category';
            this.newSiteUrl = null;
            this.editSiteId = null;
        }
        this.showAdd = true;
        this.siteError = null;

        this._inputEl = this._element.querySelector('#site-name');
        if (this._inputEl != null) {
            // Allow Angular to digest showAdd before trying to focus. (Can't
            // focus a hidden element.)
            new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
        }
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('#site-name');
    }

    /// Hide the add/edit sites dialog.
    void hideAddDialog() {
        this.showAdd = false;
    }

    /// Select a category in the "Add Site" form.
    void setSiteCategory(String category) {
        this.newSiteCategory = category;
        String categoryHuman = category.replaceRange(0, 1, category[0].toUpperCase());
        this.newSiteCategoryDescription = categoryHuman;
    }

    /// Set site for deletion and show confirmation modal
    void setDeleteId(String id_) {
        this.deleteSiteId = id_;
        String selector = '#confirm-delete-modal';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).show();
    }

    /// Set site for deletion and show confirmation modal
    void showTestSiteDialog(String id_) {
        this.testSiteId = id_;
	this.testing = false;
	this.result = null;
	this.testError = null;
        String selector = '#test-site-modal';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).show();

        this._inputEl = this._element.querySelector('#username-query');
        if (this._inputEl != null) {
            // Allow Angular to digest showTestDialog before trying to focus. (Can't
            // focus a hidden element.)
	    // Modals take around a second to render.
            new Timer(new Duration(seconds:1.2), () => this._inputEl.focus());
        }
    }

    /// Set site to be edited and show add/edit dialog.
    void editSite(int id_) {
        this.newSiteName = this.sites[id_].name;
        this.setSiteCategory(this.sites[id_].category);
        this.newSiteSearchText = this.sites[id_].searchText;
        this.newSiteStatusCode = this.sites[id_].statusCode;
        this.newSiteUrl = this.sites[id_].url;
        this.editSiteId = id_;
        this.showAddDialog('edit');
    }

    /// Fetch a page of profiler sites.
    void _fetchCurrentPage() {
        this.loading++;
        String pageUrl = '/api/site/';
        Map urlArgs = {
            'page': this._queryWatcher['page'] ?? '1',
            'rpp': this._queryWatcher['rpp'] ?? '10',
        };

        this.sites = new Map<String>();

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.sites = new Map<String>();

                response.data['sites'].forEach((site) {
                    this.sites[site['id']] = new Site.fromJson(site);
                });
                this.siteIds = new List<String>.from(this.sites.keys);

                this.pager = new Pager(response.data['total_count'],
                                       int.parse(this._queryWatcher['page'] ?? '1'),
                                       resultsPerPage:int.parse(this._queryWatcher['rpp'] ?? '10'));

            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {this.loading--;});
    }

    // Fetch list of site categories.
    void _fetchCategories() {
        this.loading++;
        String categoriesUrl = '/api/site/categories';
        this.siteCategories = new List();
        Map urlArgs = new Map();

        this.api
            .get(categoriesUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                response.data['categories'].forEach((category) {
                    this.siteCategories.add(category);

                });
                this.siteCategories.sort();
            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {
                this.loading--;
            });
    }

    /// Validate site input form
    bool _validateSiteInput() {
        bool result = true;

        if (this.newSiteCategory == '' || this.newSiteCategory == null) {
            this.siteError = 'You must select a site category.';
            result = false;
        }

        if (this.newSiteSearchText == '' || this.newSiteSearchText == null) {
            this.siteError = 'You must enter search text for the site.';
            result = false;
        }

        try {
            int code = int.parse(this.newSiteStatusCode);
        } on FormatException {
            this.siteError = 'Status code must be a number.';
            result = false;
        } on ArgumentError {
            this.siteError = 'Status code must be a number.';
            result = false;
        }

        if (this.newSiteUrl == '' || this.newSiteUrl == null) {
            this.siteError = 'You must enter a URL for the site.';
            result = false;
        }

        if (this.newSiteName == '' || this.newSiteName == null) {
            this.siteError = 'You must enter a name for the site.';
            result = false;
        }

        return result;
    }

    /// Submit a new site.
    void addSite(Event e, dynamic data, Function resetButton) {
        String pageUrl = '/api/site/';
        this.siteError = null;
        this.submittingSite = true;
        this.loading++;

        // Validate input
        bool valid = this._validateSiteInput();
        if(!valid) {
            this.submittingSite = false;
            resetButton();
            this.loading--;
            return;
        }

        Map site = {
            'name': this.newSiteName,
            'url': this.newSiteUrl,
            'category': this.newSiteCategory,
            'search_text': this.newSiteSearchText,
            'status_code': this.newSiteStatusCode,
        };

        Map body = {
            'sites': [site]
        };

        this.api
            .post(pageUrl, body, needsAuth: true)
            .then((response) {
                String msg = 'Added site ${this.newSiteName}';
                this._showMessage(msg, 'success', 3, true);
                this._fetchCurrentPage();
                this.showAdd = false;
            })
            .catchError((response) {
                this.siteError = response.data['message'];
            })
            .whenComplete(() {
                this.submittingSite = false;
                this.loading--;
                resetButton();
            });
    }

    /// Trigger add site when the user presses enter in the site input.
    void handleAddSiteKeypress(Event e) {
        if (e.charCode == 13) {
            addSite();
        }
    }


    /// Trigger test site when the user presses enter in the test site input.
    void handleTestSiteKeypress(Event e) {
        if (e.charCode == 13) {
            testSite();
        }
    }

    /// Listen for site updates.
    void _siteListener(Event e) {
        Map json = JSON.decode(e.data);

        if (json['error'] == null) {
            if (json['status'] == 'created') {
                this._showMessage('Site "${json["name"]}" created.', 'success', 3);
            }
            else if (json['status'] == 'updated') {
                this._showMessage('Site "${json["name"]}" updated.', 'info', 3);
            }
            else if (json['status'] == 'deleted') {
                this._showMessage('Site "${json["name"]}" deleted.', 'danger', 3);
            }
            this._fetchCurrentPage();
        }
    }

   /// Convert string to camel case.
   String toCamelCase(String input, String separator) {
        List components = input.split(separator);
        if(components.length > 1) {
            String camelCase = components[0];
            for(var i=1; i < components.length; i++) {
                String initial = components[i].substring(0, 1).toUpperCase();
                String word = initial + components[i].substring(1);
                camelCase += word;
            }
            return camelCase;
        }
        return input;
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

    /// Save an edited site.
    void saveSite(Event e, dynamic data, Function resetButton) {
        String pageUrl = '/api/site/${this.editSiteId}';
        this.loading++;

        Map body = {
            'name': this.newSiteName,
            'url': this.newSiteUrl,
            'status_code': this.newSiteStatusCode,
            'search_text': this.newSiteSearchText,
            'category': this.newSiteCategory,
        };

        this.api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                String name = this.sites[editSiteId].name;
                this._fetchCurrentPage();
                this.showAdd = false;
                this._showMessage('Updated site ${name}', 'info', 3, true);
            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {
                this.loading--;
                resetButton();
            });
    }

    // Request username search for testSiteId.
    void testSite() {
	this.result = null;
        if (this.query == null || this.query == '') {
            this.testError = 'You must enter a username query';
            return;
        } else {
            this.testError = null;
        }

        if(this.testSiteId == null) {
            return;
        }

	this.testing = true;

        String pageUrl = '/api/username/';

        Map urlArgs = {
            'usernames': [this.query],
	    'site': this.testSiteId,
	    'archive': false
        };

        this.api
            .post(pageUrl, urlArgs, needsAuth: true)
            .then((response) {
                this.trackerId = response.data['tracker_ids'][this.query];
                this.query = '';
                new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
            })
            .catchError((response) {
                this.testError = response.data['message'];
            })
            .whenComplete(() {});
    }


    /// Delete site specified by deleteSiteId.
    void deleteSite(Event e, dynamic data, Function resetButton) {
        if(this.deleteSiteId == null) {
            return;
        }
        String pageUrl = '/api/site/${this.deleteSiteId}';
        String name = this.sites[deleteSiteId].name;
        this.loading++;

        this.api
            .delete(pageUrl, needsAuth: true)
            .then((response) {
                this._showMessage('Deleted site ${name}', 'danger', 3, true);
                this._fetchCurrentPage();
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

    /// Get the index of a site category element.
    int siteCategoryIndex(String category) {
        int index;
        for (int i = 0; i < this.siteCategories.length; i++) {
            if(category == this.siteCategories[i]) {
                index = i;
                break;
            }
        }
        return index;
    }

    /// Listen for job results.
    void _resultListener(Event e) {
        Map json = JSON.decode(e.data);
	window.console.debug(json);
        Result result = new Result.fromJson(json);
        if (result.trackerId == this.trackerId) {
            this.result = result;
	    // Turn off loading spinner
	    this.testing = false;
        }
    }
}
