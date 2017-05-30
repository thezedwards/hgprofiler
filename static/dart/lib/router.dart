import 'package:angular/angular.dart';
import 'package:hgprofiler/authentication.dart';
import 'package:hgprofiler/redirect.dart';

/// Configures routes for the application.
@Injectable()
class HGProfilerRouteInitializer implements Function {
    AuthenticationController auth;

    HGProfilerRouteInitializer(this.auth);

    /// Configures routes for the application.
    ///
    /// Although the router allows hierarchical routes, we opted for "flat"
    /// routes based on discussion on GitHub:
    /// https://github.com/angular/route.dart/issues/69#issuecomment-81612794
    void call(Router router, RouteViewFactory views) {
        views.configure({
            'admin': ngRoute(
                path: '/admin',
                preEnter: auth.requireLogin,
                viewHtml: '<admin-index></admin-index>'
            ),
            'background_tasks': ngRoute(
                path: '/admin/background-tasks',
                preEnter: auth.requireLogin,
                viewHtml: '<background-tasks></background-tasks>'
            ),
            'configuration': ngRoute(
                path: '/admin/configuration',
                preEnter: auth.requireLogin,
                viewHtml: '<configuration-list></configuration-list>'
            ),
            'proxies': ngRoute(
                path: '/admin/proxies',
                preEnter: auth.requireLogin,
                viewHtml: '<proxy-list></proxy-list>'
            ),
            //'home': ngRoute(
            //    path: '/',
            //    preEnter: auth.requireLogin,
            //    viewHtml: '<home></home>'
            //),
            'login': ngRoute(
                path: '/login',
                preEnter: auth.requireNoLogin,
                viewHtml: '<login></login>'
            ),
            'redirect': ngRoute(
                path: '/redirect/:url',
                preEnter: redirect
            ),
            'site': ngRoute(
                path: '/site',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<site></site>'
            ),
            'username':ngRoute(
                path: '/',
                preEnter: auth.requireLogin,
                viewHtml: '<username></username>'
            ),
            'user_list': ngRoute(
                path: '/user',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<user-list></user-list>'
            ),
            'user_credit':ngRoute(
                path: '/user/:id/credit',
                preEnter: auth.requireLogin,
                viewHtml: '<user-credit></user-credit>'
            ),
            'user_view':ngRoute(
                path: '/user/:id',
                preEnter: auth.requireLogin,
                viewHtml: '<user></user>'
            ),
            'category_list':ngRoute(
                path: '/category',
                preEnter: auth.requireLogin,
                viewHtml: '<category-list></category-list>'
            ),
            'archive_list':ngRoute(
                path: '/archive',
                preEnter: auth.requireLogin,
                viewHtml: '<archive></archive>'
            ),

        });
    }
}

