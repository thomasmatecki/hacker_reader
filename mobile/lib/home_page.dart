import 'package:flutter/material.dart';
import 'package:hacker_reader/story.dart';
import 'package:http/http.dart' as http;
import 'package:infinite_scroll_pagination/infinite_scroll_pagination.dart';

import 'dart:async';
import 'dart:convert';

OverlayEntry? overlayEntry;

removeOverlay() {
  overlayEntry?.remove();
  overlayEntry = null;
}

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
  });

  @override
  State<HomePage> createState() => _HomePageState();
}

class _StoryTile extends StatelessWidget {
  const _StoryTile({
    required this.story,
  });

  final Story story;

  @override
  Widget build(BuildContext context) {
    return InkWell(
        onTap: () {
          removeOverlay();
          Navigator.pushNamed(
            context,
            '/detail',
            arguments: story,
          );
        },
        child: Padding(
          padding: const EdgeInsets.fromLTRB(7.5, 5.0, 7.5, 0.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                story.title,
                style: const TextStyle(
                  fontWeight: FontWeight.w500,
                  fontSize: 16.0,
                ),
              ),
              const Padding(
                  padding: EdgeInsets.symmetric(
                vertical: 1.0,
              )),
              if (story.url != null)
                Text(
                  story.url!,
                  style: const TextStyle(fontSize: 10.0),
                ),
              const Padding(padding: EdgeInsets.symmetric(vertical: 1.0)),
              Text(
                '${story.score} views by ${story.by} | ${story.comments} comments',
                style: const TextStyle(fontSize: 10.0),
              ),
              const Divider(),
            ],
          ),
        ));
  }
}

class _HomePageState extends State<HomePage> with TickerProviderStateMixin {
  final PagingController<int, Story> _pagingController =
      PagingController(firstPageKey: 1);

  final ScrollController _scrollController = ScrollController();

  final _pageSize = 20;

  @override
  void initState() {
    _pagingController.addPageRequestListener((pageKey) {
      _fetchPage(pageKey);
    });
    super.initState();
  }

  @override
  void dispose() {
    _pagingController.dispose();
    super.dispose();
  }

  void addOverlay() {
    if (overlayEntry != null) {
      return;
    }

    overlayEntry = OverlayEntry(
      // Create a new OverlayEntry.
      builder: (BuildContext context) {
        final ButtonStyle style = ElevatedButton.styleFrom(
          textStyle: const TextStyle(fontSize: 16),
          fixedSize: const Size(100.00, 14.00),
          elevation: 20.00,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(30.0),
          ),
        );

        final AnimationController controller = AnimationController(
          duration: const Duration(milliseconds: 500),
          vsync: this,
        )..forward();

        final Animation<double> animation = CurvedAnimation(
          parent: controller,
          curve: Curves.easeIn,
        );

        // Align is used to position the highlight overlay
        // relative to the NavigationBar destination.
        return Positioned(
            top: kToolbarHeight + 5,
            left: 0,
            right: 0,
            child: Container(
                alignment: Alignment.topCenter,
                child: SafeArea(
                  child: FadeTransition(
                    opacity: animation,
                    child: ElevatedButton(
                        style: style,
                        onPressed: () {
                          _scrollController.animateTo(
                            0,
                            duration: const Duration(
                              milliseconds: 500,
                            ),
                            curve: Curves.fastOutSlowIn,
                          );
                        },
                        child: Row(
                          children: const [
                            Icon(Icons.arrow_upward, color: Colors.black54),
                            Text('Top', style: TextStyle(color: Colors.black54))
                          ],
                        )),
                  ),
                )));
      },
    );

    // Add the OverlayEntry to the Overlay.
    Overlay.of(context, debugRequiredFor: widget).insert(overlayEntry!);
  }

  Future<void> _fetchPage(int pageNumber) async {
    http.Response apiResponse = await http
        .get(Uri.parse("http://localhost:8000/stories/?page=$pageNumber"));

    Map<String, dynamic> decodedResponse = jsonDecode(apiResponse.body);
    List<Story> fetchedStories =
        List.from(decodedResponse["results"].map((r) => Story.fromJson(r)));
    final isLastPage = fetchedStories.length < _pageSize;
    if (isLastPage) {
      _pagingController.appendLastPage(fetchedStories);
    } else {
      final nextPageNumber = pageNumber + 1;
      _pagingController.appendPage(fetchedStories, nextPageNumber);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(
          title: const Text("Hacker News"),
        ),
        body: NotificationListener(
            onNotification: (ScrollNotification scrollInfo) {
              ScrollMetrics metrics = scrollInfo.metrics;
              if (metrics.pixels > metrics.viewportDimension / 2) {
                addOverlay();
              } else {
                removeOverlay();
              }
              return true;
            },
            child: Padding(
              padding: const EdgeInsets.fromLTRB(0.0, 7.5, 0.0, 0.0),
              child: RefreshIndicator(
                onRefresh: () => Future.sync(
                  () => _pagingController.refresh(),
                ),
                child: PagedListView<int, Story>(
                  pagingController: _pagingController,
                  scrollController: _scrollController,
                  builderDelegate: PagedChildBuilderDelegate<Story>(
                    itemBuilder: (context, item, index) => _StoryTile(
                      story: item,
                    ),
                  ),
                ),
              ),
            )));
  }
}
