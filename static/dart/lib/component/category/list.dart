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
import 'package:hgprofiler/component/title.dart';
import 'package:hgprofiler/model/category.dart';
import 'package:hgprofiler/model/site.dart';
import 'package:hgprofiler/rest_api.dart';
import 'package:hgprofiler/sse.dart';

/// A component for viewing and modifying credentials.
@Component(
    selector: 'category-list',
    templateUrl: 'packages/hgprofiler/component/category/list.html',
    useShadowDom: false
)
class CategoryListComponent extends Object
                    implements ShadowRootAware {

    bool allSites = false;
    List<Breadcrumb> crumbs = [
        new Breadcrumb('Profiler', '/'),
        new Breadcrumb('Categories', '/category'),
    ];
    int deleteCategoryId;
    String dialogTitle;
    String dialogClass;
    int editCategoryId;
    List<int> editCategorySiteIds;
    final Element _element;
    List<CheckboxInputElement> editSiteCheckboxes;
    String categoryError;
    List<String> categoryIds;
    Map<Map> categories;
    int loading = 0;
    List<Map> messages = new List<Map>();
    String newCategoryName;
    Pager pager;
    bool showAdd = false;
    List<Site> sites;
    String siteSearch = '';
    bool submittingCategory = false;
    int totalSites;

    InputElement _inputEl;
    Router _router; QueryWatcher _queryWatcher;
    final AuthenticationController _auth;
    final RestApiController _api;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    CategoryListComponent(this._auth, this._api, this._element,
                       this._router, this._rp, this._sse, this._ts) {

        this._ts.title = 'Categories';

        RouteHandle rh = this._rp.route.newHandle();
        this._queryWatcher = new QueryWatcher(
            rh,
            ['page', 'rpp'],
            this._fetchCurrentPage
        );

        // Add event listeners...
        UnsubOnRouteLeave(rh, [
            this._sse.onCategory.listen(this._categoryListener),
        ]);

        this._fetchSites();
        this._fetchCurrentPage();
    }

    /// Show the "add profile" dialog.
    void showAddDialog(String mode) {
        if(mode == 'edit') {
            this.dialogTitle = 'Edit Category';
            this.dialogClass = 'panel-info';
        } else {
            this.dialogTitle = 'Add Category';
            this.dialogClass = 'panel-success';
            this.newCategoryName = '';
            String selector = 'input[name="add-site-checkbox"][type="checkbox"]';
            List<CheckboxInputElement> siteCheckboxes = this._element.querySelectorAll(selector);
            siteCheckboxes.forEach((checkbox) {
                checkbox.checked = false;
            });
            String toggleSelector = '#all-sites-toggle[type="checkbox"]';
            CheckboxInputElement toggleSiteCheckbox = this._element.querySelector(toggleSelector);
            toggleSiteCheckbox.checked = false;
        }

        this.showAdd = true;
        this.categoryError = null;

        this._inputEl = this._element.querySelector('#category-name');
        if (this._inputEl != null) {
            // Allow Angular to digest showAdd before trying to focus. (Can't
            // focus a hidden element.)
            new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
        }
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('.add-category-form input');
    }

    /// Show the "add categories" dialog.
    void hideAddDialog() {
        this.showAdd = false;
        this.editCategoryId = null;
    }

    /// Fetch a page of profiler categories.
    Future _fetchCurrentPage() {
        Completer completer = new Completer();
        this.loading++;
        String pageUrl = '/api/category/';
        Map urlArgs = {
            'page': this._queryWatcher['page'] ?? '1',
            'rpp': this._queryWatcher['rpp'] ?? '100',
        };
        this.categories = new Map<Map>();

        this._api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.categoryIds = new List<String>();

                response.data['categories'].forEach((category) {
                    this.categories[category['id']] = {
                        'name': category['name'],
                        'sites': new List.generate(
                            category['sites'].length,
                            (index) => new Site.fromJson(category['sites'][index])
                        ),
                    };
                });
                this.categoryIds = new List<String>.from(this.categories.keys);

                this.pager = new Pager(response.data['total_count'],
                                       int.parse(this._queryWatcher['page'] ?? '1'),
                                       resultsPerPage: int.parse(this._queryWatcher['rpp'] ?? '100'));

            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });
        return completer.future;
    }

    void saveCategory(Event e, dynamic data, Function resetButton) {
        String selector = 'input[name="add-site-checkbox"][type="checkbox"]:checked';
        List<CheckboxInputElement> siteCheckboxes = this._element.querySelectorAll(selector);
        this.editCategorySiteIds = new List();
        siteCheckboxes.forEach((checkbox) {
            this.editCategorySiteIds.add(checkbox.value);
        });

        // Validate input
        bool valid = this._validateCategoryInput();
        if(!valid) {
            this.submittingCategory = false;
            resetButton();
            this.loading--;
            return;
        }


        String pageUrl = '/api/category/${this.editCategoryId}';
        this.loading++;

        Map body = {
            'name': this.newCategoryName,
            'sites':  this.editCategorySiteIds
        };

        this._api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                this._fetchCurrentPage();
                this.showAdd = false;
                this._showMessage('Updated category ${this.newCategoryName}', 'success', 3, true);
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

    /// Set category for deletion and show confirmation modal
    void setDeleteId(String id_) {
        this.deleteCategoryId = id_;
        String selector = '#confirm-delete-modal';
        DivElement modalDiv = this._element.querySelector(selector);
        Modal.wire(modalDiv).show();
    }

    /// Delete category specified by deleteCategoryId.
    void deleteCategory(Event e, dynamic data, Function resetButton) {
        if(this.deleteCategoryId == null) {
            return;
        }

        String pageUrl = '/api/category/${this.deleteCategoryId}';
        String name = this.categories[deleteCategoryId]['name'];
        this.loading++;
        Map body = {};

        this._api
            .delete(pageUrl, urlArgs: {}, needsAuth: true)
            .then((response) {
                this._showMessage('Deleted category ${name}', 'success', 3, true);
                this._fetchCurrentPage();
            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            })
            .whenComplete(() {
                this.loading--;
                Modal.wire($("#confirm-delete-modal")).hide();
                resetButton();
            });
    }

    /// Set category to be edited and show add/edit dialog.
    void editCategory(int id_) {
        this.newCategoryName = this.categories[id_]['name'];
        this.siteSearch = '';
        this.editCategoryId = id_;
        this.showAddDialog('edit');
        this.editCategorySiteIds = new List.generate(
                this.categories[id_]['sites'].length,
                (index) =>  this.categories[id_]['sites'][index].id);
        String selector = 'input[name="add-site-checkbox"][type="checkbox"]';
        List<CheckboxInputElement> siteCheckboxes = this._element.querySelectorAll(selector);
        siteCheckboxes.forEach((checkbox) {
            if (this.editCategorySiteIds.contains(int.parse(checkbox.value))) {
                checkbox.checked = true;
            } else {
                checkbox.checked = false;
            }
        });
    }

    void toggleAddSites() {
        if (this.allSites == false) {
            this.allSites = true;
        } else {
            this.allSites = false;
        }

        String selector = 'input[name="add-site-checkbox"][type="checkbox"]';
        List<CheckboxInputElement> siteCheckboxes = this._element.querySelectorAll(selector);
        this.editCategorySiteIds = new List();
        siteCheckboxes.forEach((checkbox) {
            checkbox.checked = this.allSites;
        });
    }

    void _validateCategoryInput() {

        if (this.newCategoryName == '' || this.newCategoryName == null) {
            this.categoryError = 'You must enter a name for the category';
            return  false;
        }

        var query  = $('input[name="add-site-checkbox"]:checked');
        if (query.length == 0) {
            this.categoryError = 'You must select at least one site';
            return false;
        }

        return true;
    }

    void addCategory(Event e, dynamic data, Function resetButton) {
        List<int> sites = new List();
        this.siteSearch = '';
        String pageUrl = '/api/category/';
        this.loading++;

        // Validate input
        bool valid = this._validateCategoryInput();
        if(!valid) {
            this.submittingCategory = false;
            resetButton();
            this.loading--;
            return;
        }


        var query  = $('input[name="add-site-checkbox"]:checked');
        query.forEach((checkbox) {
            sites.add(checkbox.value);
        });

        Map category  = {
            'name': this.newCategoryName,
            'sites': sites
        };

        Map body = {
            'categories': [category]
        };

        this._api
            .post(pageUrl, body, needsAuth: true)
            .then((response) {
                String msg = 'Added category ${this.newCategoryName}';
                this._showMessage(msg, 'success', 3, true);
                this._fetchCurrentPage();
                this.showAdd = false;
            })
            .catchError((response) {
                this.categoryError = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                resetButton();
                this.submittingCategory = false;
            });
    }


    /// Fetch a page of profiler sites.
    Future _fetchPageOfSites(int index) {
        Completer completer = new Completer();
        this.loading++;
        String siteUrl = '/api/site/';
        Map urlArgs = {
            'page': index,
            'rpp': 100,
        };
        int totalCount = 0;
        Map result = new Map();

        this._api
            .get(siteUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                if (response.data.containsKey('total_count')) {
                    this.totalSites = response.data['total_count'];
                }
                response.data['sites'].forEach((siteJson) {
                    Site site = new Site.fromJson(siteJson);
                    if (!this.sites.contains(site)) {
                        this.sites.add(site);
                    }
                });
                this.loading--;
                completer.complete();
            })
            .catchError((response) {
                String msg = response.data['message'];
                this._showMessage(msg, 'danger');
            });
        return completer.future;
    }

    // Fetch all profiler sites.
    Future _fetchSites() {
        Completer completer = new Completer();
        Map result;
        bool finished = false;
        int page = 1;
        this.sites = new List();
        String siteUrl = '/api/site/';
        int totalCount = 0;
        this._fetchPageOfSites(page)
            .then((_) {
                int lastPage = (this.totalSites/100).ceil();
                page++;
                while(page <= lastPage) {
                    this._fetchPageOfSites(page);
                    page++;
                }
                completer.complete();

            });
        return completer.future;
    }

    /// Trigger add category when the user presses enter in the category input.
    void handleAddCategoryKeypress(Event e) {
        if (e.charCode == 13) {
            addCategory();
        }
    }

    /// Listen for category updates.
    void _categoryListener(Event e) {
        Map json = JSON.decode(e.data);
        window.console.debug(json);

        if (json['error'] == null) {
            if (json['status'] == 'created') {
                this._showMessage('Category "${json["name"]}" created.', 'success', 3);
            }
            else if (json['status'] == 'updated') {
                this._showMessage('Category "${json["name"]}" updated.', 'info', 3);
            }
            else if (json['status'] == 'deleted') {
                this._showMessage('Category "${json["name"]}" deleted.', 'danger', 3);
            }
            this._fetchCurrentPage();
        }
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
}
