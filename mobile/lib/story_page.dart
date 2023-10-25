import 'package:flutter/material.dart';
import 'package:hacker_reader/comments_tab.dart';
import 'package:hacker_reader/story.dart';
import 'package:webview_flutter/webview_flutter.dart';

class StoryPage extends StatefulWidget {
  const StoryPage({super.key});

  @override
  State<StoryPage> createState() => _StoryPageState();
}

class _StoryPageState extends State<StoryPage> {
  late final WebViewController _controller;
  late final List<Widget> _widgetOptions;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController();
    _widgetOptions = <Widget>[
      WebViewWidget(
        controller: _controller,
      ),
      CommentsTab()
    ];
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final story = ModalRoute.of(context)!.settings.arguments as Story;
    if (story.url != null) {
      _controller.loadRequest(
        Uri.parse(story.url!),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(story.title),
      ),
      body: Center(child: _widgetOptions.elementAt(_selectedIndex)),
      bottomNavigationBar: BottomNavigationBar(
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(
            icon: Icon(Icons.view_array),
            label: 'Content',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.comment),
            label: 'Comments',
          ),
        ],
        currentIndex: _selectedIndex,
        selectedItemColor: Colors.amber[800],
        onTap: _onItemTapped,
      ),
    );
  }
}
