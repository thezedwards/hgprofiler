/// A model for a proxy.
class Proxy {

    int id;
    String host;
    int port;
    String protocol;
    String username;
    String password;
    bool active;

    Proxy(String protocol, String host, int port,
            String username, String password, bool active) {
        this.host = host;
        this.port = port;
        this.protocol = protocol;
        this.username = username;
        this.password = password;
        this.active = active;
    }

    Proxy.fromJson(Map json) {
        this.id = json['id'];
        this.host = json['host'];
        this.port = json['port'];
        this.protocol = json['protocol'];
        this.username = json['username'];
        this.password = json['password'];
        this.active = json['active'];
    }
}
