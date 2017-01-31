/// A model for a username search result.
class Result {

    int id;
    String trackerId;
    String siteName;
    String siteUrl;
    int imageFileId;
    String imageFileUrl;
    int number;
    String status;
    int total;
    String error;
    String username;
    DateTime completed_at;

    Result(String trackerId, String siteName, String siteUrl,
            String status, int number, int total, String username,
            DateTime completed_at) {
        this.status = status;
        this.trackerId = trackerId;
        this.siteName = siteName;
        this.siteUrl = siteUrl;
        this.number = number;
        this.total = total;
        this.username = username;
        this.completed_at = completed_at;
    }

    Result.fromJson(Map json) {
        this.status = json['status'];
        this.id = json['id'];
        this.trackerId = json['tracker_id'];
        this.siteName = json['site_name'];
        this.siteUrl = json['site_url'];
        this.imageFileId = json['image_file_id'];
        this.imageFileUrl = json['image_file_url'];
        this.number = json['number'];
        this.total = json['total'];
        this.error = json['error'];
        this.username = json['username'];
        this.completed_at = DateTime.parse(json['completed_at']);
    }
}
