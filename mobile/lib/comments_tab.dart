import 'package:flutter/material.dart';
import 'package:hacker_reader/story.dart';

class CommentsTab extends StatefulWidget {
  @override
  State<StatefulWidget> createState() {
    // TODO: implement createState
    throw UnimplementedError();
  }
}

class _CommentsTabState extends State<CommentsTab> {
  @override
  Widget build(BuildContext context) {
    final story = ModalRoute.of(context)!.settings.arguments as Story;
    return Text(story.title);
  }
}
