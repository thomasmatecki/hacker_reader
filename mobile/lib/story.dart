class Story {
  int id;
  String title;
  String? url;
  int score;
  int comments;
  String by;

  Story(this.id, this.title, this.url, this.score, this.by, this.comments);

  Story.fromJson(Map<String, dynamic> json)
      : id = json["id"],
        title = json['title'],
        url = json['url'],
        score = json['score'],
        by = json['by'],
        comments = json['descendants'];
}
