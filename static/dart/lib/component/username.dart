import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dquery/dquery.dart';

import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/component/breadcrumbs.dart';
import 'package:hgprofiler/component/pager.dart';
import 'package:hgprofiler/component/title.dart';
import 'package:hgprofiler/model/archive.dart';
import 'package:hgprofiler/model/result.dart';
import 'package:hgprofiler/model/category.dart';
import 'package:hgprofiler/rest_api.dart';
import 'package:hgprofiler/sse.dart';

/// A controller for searching websites for usernames.
@Component(
    selector: 'username',
    templateUrl: 'packages/hgprofiler/component/username.html',
    useShadowDom: false
)
class UsernameComponent implements ShadowRootAware {
    Archive archive;
    String archiveFile;
    Map backgroundTask;
    List<Breadcrumb> crumbs = [
        new Breadcrumb('Profiler', '/'),
    ];
    Map<int> categoryCost = new Map<int>();
    int currentPage;
    int cost;
    String error;
    int found;
    String filter;
    String filterDescription = 'All';
    Category selectedCategory;
    List<Category> categories;
    String categoryDescription = 'All Sites';
    int loading = 0;
    String trackerId;
    List<Result> results;
    bool submittingUsername = false;
    bool awaitingResults = false;
    Pager pager;
    String query;
    int resultsPerPage = 10;
    Result screenshotResult;
    String screenshotClass;
    int totalResults;
    int totalCategories;
    int totalSitesCost;
    String username;
    String sort, sortDescription;
    List<String> urls;

    InputElement _inputEl;

    final AuthenticationController _auth;
    final Element _element;
    final RestApiController api;
    final RouteProvider _rp;
    final Router _router;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor
    UsernameComponent(this.api, this._auth, this._element, this._rp, this._router, this._sse, this._ts) {
        // Get the current query parameters from URL...
        var route = this._rp.route;
        this._parseQueryParameters(route.queryParameters);
        this._ts.title = 'Usernames';

        // Add event listeners...
        RouteHandle rh = route.newHandle();

        // Add event listeners...
        UnsubOnRouteLeave(rh, [
            this._sse.onResult.listen(this._resultListener),
            this._sse.onArchive.listen(this._archiveListener),
            rh.onEnter.listen((e) {
                this._parseQueryParameters(e.queryParameters);
                this._fetchCurrentPage();
            }),
        ]);

        this._fetchCategories();
    }

    // Request username search from background workers.
    void searchUsername() {
        if (this.query == null || this.query == '') {
            this.error = 'You must enter a username query';
            return;
        } else {
            this.error = null;
        }
        this.submittingUsername = true;
        this.awaitingResults = true;
        this.results = new List<Result>();
        this.cost = 0;
        this.totalResults = 0;
        this.found = 0;
        this.username = this.query;

        String pageUrl = '/api/username/';

        Map urlArgs = {
            'usernames': [this.query]
        };

        if (this.selectedCategory != null) {
            urlArgs['category'] = this.selectedCategory.id;
        }

        this.api
            .post(pageUrl, urlArgs, needsAuth: true)
            .then((response) {
                this.trackerId = response.data['tracker_ids'][this.query];
                this.query = '';
                new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.submittingUsername = false;});
    }

    /// Confirm search username
    void confirmSearch() {
        String selector = '#confirm';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).hide();
        this.searchUsername();
    }

    /// Show confirmation modal
    void showConfirmModal() {
        String selector = '#confirm';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).show();
    }

    void setCategory(Category category) {
        this.selectedCategory = category;
        if(category == null) {
            this.categoryDescription = 'All Sites';
        } else {
            this.categoryDescription = category.name;
        }
    }

    void setFilter(String filter) {
        this.filter = filter;
        if(filter == null) {
            this.filterDescription = 'All';
        } else {
            this.filterDescription = filter;
        }
    }

    void setScreenshotResult(Result result) {
        this.screenshotResult = result;
        if (result.status == 'f') {
            this.screenshotClass = 'found';
        }
        else if (result.status == 'n') {
            this.screenshotClass = 'not-found';
        }
        else if (result.status == 'e') {
            this.screenshotClass = 'error';
        }
    }

    void showResult(Result result) {
        if (this.filter == null) {
            return true;
        }
        if (this.filter == 'Found' && result.status == 'f') {
            return true;
        }
        if (this.filter == 'Not Found' && result.status == 'n') {
            return true;
        }
        if (this.filter == 'Error' && result.status == 'e') {
            return true;
        }
        return false;
    }

    /// Fetch a page of profiler site categories.
    Future _fetchPageOfCategories(page) {
        Completer completer = new Completer();
        this.loading++;
        String categoryUrl = '/api/categories/';
        Map urlArgs = {
            'page': page,
            'rpp': 100,
        };
        int totalCount = 0;
        this.api
            .get(categoryUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                if (response.data.containsKey('total_count')) {
                    this.totalCategories = response.data['total_count'];
                }
                response.data['categories'].forEach((category) {
                    if (!this.categories.contains(category)) {
                        this.categories.add(new Category.fromJson(category));
                    }
                });
                this.totalSitesCost = response.data['total_valid_sites'];
                this.loading--;
                completer.complete();
            })
            .catchError((response) {
                this.error = response.data['message'];
            });
        return completer.future;
    }

    // Fetch all profiler categories.
    Future _fetchCategories() {
        Completer completer = new Completer();
        Map result;
        this.error = null;
        int page = 1;
        this.categories = new List();
        this._fetchPageOfCategories(page)
            .then((_) {
                int lastPage = (this.totalCategories/100).ceil();
                page++; while(page <= lastPage) {
                    this._fetchPageOfCategories(page);
                    page++;
                }
                completer.complete();

            });
        return completer.future;
    }

    /// Listen for job results.
    void _resultListener(Event e) {
        Map json = JSON.decode(e.data);
        Result result = new Result.fromJson(json);
        if (result.trackerId == this.trackerId) {
            this.results.add(result);
            this.totalResults = result.total;
            if(result.status == 'f') {
                this.found++;
            }
            if (result.status != 'e') {
                this.cost++;
            }
            if(this.totalResults == this.results.length) {
                new Timer(new Duration(seconds:1), () {
                    this.awaitingResults = false;
                });
            }
        }
    }

    /// Listen for archive results.
    void _archiveListener(Event e) {
        Map json = JSON.decode(e.data);
        Archive archive = new Archive.fromJson(json['archive']);
        if (archive.trackerId == this.trackerId) {
            this.archive = archive;
        }
    }

    /// Handle a keypress in the search input field.
    void handleSearchKeypress(event) {
        window.console.debug(event.keyCode);
        window.console.debug(KeyCode.ENTER);
        if (event.keyCode == KeyCode.ENTER) {
            this.showConfirmModal();
        }
    }

    /// Sort by a specified field.
    void sortBy(String sort) {
        Map args = this._makeUrlArgs();
        args.remove('page');

        if (sort == null) {
            args.remove('sort');
        } else {
            args['sort'] = sort;
        }

        this._router.go('search',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Get a query parameter as an int.
    void _getQPInt(value, [defaultValue]) {
        if (value != null) {
            return int.parse(value);
        } else {
            return defaultValue;
        }
    }

    /// Get a query parameter as a string.
    void _getQPString(value, [defaultValue]) {
        if (value != null) {
            return Uri.decodeComponent(value);
        } else {
            return defaultValue;
        }
    }

    /// Make a map of arguments for a URL query string.
    void _makeUrlArgs() {
        var args = new Map<String>();

        // Create query, page, and sort URL args.
        if (this.currentPage != 1) {
            args['page'] = this.currentPage.toString();
        }

        if (this.query != null && !this.query.trim().isEmpty) {
            args['query'] = this.query;
        }

        if (this.resultsPerPage != 10) {
            args['rpp'] = this.resultsPerPage.toString();
        }

        if (this.sort != null) {
            args['sort'] = this.sort;
        }

        return args;
    }

    /// Take a map of query parameters and parse/load into member variables.
    void _parseQueryParameters(qp) {
        this.error = null;

        // Set up query and paging URL args.
        this.currentPage = this._getQPInt(qp['page'], 1);
        this.query = this._getQPString(qp['query']);
        this.resultsPerPage = this._getQPInt(qp['rpp'], 10);


        // Set up breadcrumbs.
        if (this.query == null) {
            this.crumbs = [
                new Breadcrumb('Profiler', '/'),
                new Breadcrumb('Usernames'),
            ];
            this._ts.title = 'Username';
        } else {
            this.crumbs = [
                new Breadcrumb('Profiler', '/'),
                new Breadcrumb('Usernames', '/username'),
                new Breadcrumb('"' + this.query + '"'),
            ];
            this._ts.title = 'Username "${this.query}"';
        }

        // Set up sort orders.
        this.sort = this._getQPString(qp['sort']);

        Map sortDescriptions = {
            'post_date_tdt': 'Post Date (Old→New)',
            '-post_date_tdt': 'Post Date (New→Old)',
            'username_s': 'Username (A→Z)',
            '-username_s': 'Username (Z→A)',
        };

        if (sortDescriptions.containsKey(this.sort)) {
            this.sortDescription = sortDescriptions[this.sort];
        } else {
            this.sortDescription = 'Most Relevant';
        }
    }

    /// Listen for changes in route parameters.
    void _routeListener(Event e) {
        this._parseQueryParameters(e.queryParameters);

        if (this.query == null || this.query.trim().isEmpty) {
            this.results = new List();
        } else {
            this._fetchSearchResults();
        }
    }

    /// Listen for updates from background workers.
    void _workerListener(Event e) {
        Map job = JSON.decode(e.data);

        if (this.backgroundTask == null && job['queue'] == 'index' &&
            (job['status'] == 'started' || job['status'] == 'progress')) {

            job['Description'] = '(Loading Description...)';
            this.backgroundTask = job;

            this.api
                .get('/api/tasks/job/${job["id"]}', needsAuth: true)
                .then((response) {
                    String description = response.data['description'];
                    this.backgroundTask['description'] = description;
                });
        } else if (this.backgroundTask['id'] == job['id']) {
            if (job['status'] == 'progress') {
                this.backgroundTask['progress'] = job['progress'];
            } else if (job['status'] == 'finished') {
                this.backgroundTask = null;
            }
        }
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('.search-username-form input');
        this._inputEl.focus();
    }
}
