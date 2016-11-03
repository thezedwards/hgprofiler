import 'package:hgprofiler/model/site.dart';
/// A model site category.
class Category {

    int id;
    List<Site> sites;
    String name;

    // Errors related to creating or loading this profile.
    String error;

    Category(String name, List<Site> sites) {
        this.name = name; 
        this.sites = sites;
    }

    Category.fromJson(Map json) {
        this.id = json['id'];
        this.name = json['name'];
        this.sites = new List.generate(
            json['sites'].length,
            (index) => new Site.fromJson(json['sites'][index])
        );
    }
}
