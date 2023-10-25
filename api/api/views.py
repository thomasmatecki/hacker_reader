from urllib import parse

import requests
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView

from . import models

STORY_COMMENTS_CACHE_KEY = "story-comment-ids::{story_id}"
COMMENT_CHILDEN_CACHE_KEY = "comment-comment-ids::{comment_id}"
CHILD_COMMENTS_CACHE_KEY = "{parent_type}-comment-ids::{parent_id}"

from logging import getLogger

logger = getLogger(__name__)


class JSONResponseMixin:
    response_class = JsonResponse

    """
    A mixin that can be used to render a JSON response.
    """

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        assert context
        raise NotImplementedError


def _story_json(s):
    return {
        "id": s.item_id,
        "title": s.title,
        "by": s.by,
        "descendants": s.descendants,
        "score": s.score,
        "text": s.text,
        "url": s.url,
        "__comments__": reverse(
            "comments",
            kwargs={
                "parent_id": s.item_id,
                "parent_type": "story",
            },
        ),
    }


def _comment_json(c):
    return {"id": c.item_id, "text": c.text, "by": c.by}


class TopStoryQuery:
    def __init__(self) -> None:
        self._top_story_ids = list(cache.get_or_set("topstories", lambda: requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json(), 30))  # type: ignore
        self._stored_stories = models.Story.objects.in_bulk(
            self._top_story_ids, field_name="item_id"
        )

    def count(self):
        return len(self._top_story_ids)

    def objects(self, story_ids):
        for story_id in story_ids:
            try:
                yield self._stored_stories[story_id]
            except KeyError:
                story_json = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                ).json()
                cache.set(
                    STORY_COMMENTS_CACHE_KEY.format(story_id=story_id),
                    story_json.get("kids", []),
                )

                story, *_ = models.Story.objects.update_or_create(
                    defaults=dict(
                        title=story_json["title"],
                        by=story_json["by"],
                        descendants=story_json.get("descendants", 0),
                        score=story_json["score"],
                        url=story_json.get("url"),
                        text=story_json.get("text"),
                    ),
                    item_id=story_id,
                )
                yield story

    def __iter__(self):
        yield from self.objects(self._top_story_ids)

    def __getitem__(self, slice):
        return list(self.objects(self._top_story_ids[slice.start : slice.stop]))


class StoryListView(JSONResponseMixin, BaseListView):
    paginate_by = 20

    def get_queryset(self):
        return TopStoryQuery()

    def get_data(self, context):
        page = context["page_obj"]
        paginator = page.paginator

        (scheme, netloc, path, query, fragment) = parse.urlsplit(
            self.request.get_full_path()
        )
        query_dict = parse.parse_qs(query, keep_blank_values=True)

        next_query_dict = dict(query_dict)
        next_query_dict[self.page_kwarg] = page.next_page_number()
        query = parse.urlencode(sorted(next_query_dict.items()), doseq=True)

        next_url = parse.urlunsplit((scheme, netloc, path, query, fragment))

        return {
            "page": page.number,
            "count": paginator.count,
            "next": next_url,
            "results": [_story_json(s) for s in context["object_list"]],
        }


class StoryDetailView(JSONResponseMixin, BaseDetailView):
    queryset = models.Story.objects.all()
    slug_url_kwarg = "story_id"
    slug_field = "item_id"

    def _get_story_comments(self, story_id):
        story_json = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        ).json()
        return story_json.get("kids", [])

    def get_data(self, context):
        story = context["object"]
        comment_ids = list(
            cache.get_or_set(
                STORY_COMMENTS_CACHE_KEY.format(story_id=story.item_id),
                lambda: self._get_story_comments(story.item_id),
            )  # type: ignore
        )  # type: ignore

        stored_comments = models.Comment.objects.in_bulk(
            comment_ids, field_name="item_id"
        )
        comments = []

        for comment_id in comment_ids:
            try:
                comments.append(stored_comments[comment_id])
            except:
                comment_json = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json"
                ).json()
                comment, _ = models.Comment.objects.update_or_create(
                    defaults=dict(
                        by=comment_json.get("by"),
                        text=comment_json.get("text"),
                        parent=story,
                    ),
                    item_id=comment_id,
                )
                cache.set(
                    COMMENT_CHILDEN_CACHE_KEY.format(comment_id=comment_id),
                    comment_json.get("kids", []),
                )
                comments.append(comment)

        data = _story_json(story)
        data["comments"] = [_comment_json(c) for c in comments]
        return data


class NestedCommentsView(JSONResponseMixin, BaseListView):
    queryset = models.Comment.objects.order_by("id")
    paginate_by = 20

    def _retrieve_child_comment_ids(self, item_id):
        item_json = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        ).json()
        return item_json.get("kids", [])

    def _get_comment_results(
        self,
        comments: list[models.Comment],
        depth=3,
    ):
        current_level_comment_ids = [comment.item_id for comment in comments]
        child_comment_ids_by_id = dict()
        all_comment_ids = [] + current_level_comment_ids

        for _ in range(depth):
            next_level_ids = []
            for comment_id in current_level_comment_ids:
                child_comment_ids = self.get_child_comment_ids(
                    parent_type="comment",
                    parent_id=comment_id,
                )
                next_level_ids.extend(child_comment_ids)
                child_comment_ids_by_id[comment_id] = child_comment_ids
            all_comment_ids.extend(next_level_ids)
            current_level_comment_ids = next_level_ids

        stored_comments = models.Comment.objects.in_bulk(
            all_comment_ids, field_name="item_id"
        )

        comment_ids_for_retrieval = sorted(
            set(all_comment_ids).difference(stored_comments.keys())
        )

        for comment_id in comment_ids_for_retrieval:
            comment_json = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json"
            ).json()

            parent = stored_comments[comment_json["parent"]]

            comment, _ = models.Comment.objects.update_or_create(
                defaults=dict(
                    by=comment_json.get("by"),
                    text=comment_json.get("text"),
                    parent=parent,
                ),
                item_id=comment_id,
            )

            stored_comments[comment.item_id] = comment

        child_comments_by_id = {
            comment_id: [stored_comments[child_id] for child_id in child_comment_ids]
            for comment_id, child_comment_ids in child_comment_ids_by_id.items()
        }

        # Fetch the child ids of the leaves.
        for comment_id in current_level_comment_ids:
            child_comment_ids_by_id[comment_id] = self.get_child_comment_ids(
                parent_type="comment",
                parent_id=comment_id,
            )

        results = [
            self._comment_json(c, child_comments_by_id, child_comment_ids_by_id)
            for c in comments
        ]

        return results

    def _comment_json(self, comment, child_comments_by_id, child_comment_ids_by_id):
        child_comments = child_comments_by_id.get(comment.item_id)

        children = child_comments and [
            self._comment_json(
                child_comment, child_comments_by_id, child_comment_ids_by_id
            )
            for child_comment in child_comments
        ]

        # Populate a link if this comment had children.
        comments_url = (
            reverse(
                "comments",
                kwargs={
                    "parent_id": comment.item_id,
                    "parent_type": "comment",
                },
            )
            if child_comment_ids_by_id.get(comment.item_id)
            else None
        )

        return {
            "id": comment.item_id,
            "text": comment.text,
            "by": comment.by,
            "__comments__": comments_url,  # null if no children, else link
            "children": children,  # null if exceeded depth, else array of comments
        }

    def get_child_comment_ids(self, *, parent_id, parent_type):
        cache_key = CHILD_COMMENTS_CACHE_KEY.format(
            parent_id=parent_id,
            parent_type=parent_type,
        )

        return list(
            cache.get_or_set(
                cache_key, lambda: self._retrieve_child_comment_ids(parent_id)
            )  # type: ignore
        )  # type: ignore

    def get_queryset(self):
        comment_ids = self.get_child_comment_ids(**self.kwargs)

        parent_model = self.kwargs["parent_type"]
        parent_item_id = self.kwargs["parent_id"]

        parent_type = ContentType.objects.get_by_natural_key("api", parent_model)
        parent = parent_type.get_object_for_this_type(item_id=parent_item_id)
        stored_comment_ids = set(
            models.Comment.objects.filter(item_id__in=comment_ids).values_list(
                "item_id", flat=True
            )
        )

        for comment_id in comment_ids:
            if comment_id in stored_comment_ids:
                continue

            comment_json = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json"
            ).json()

            models.Comment.objects.update_or_create(
                defaults=dict(
                    by=comment_json.get("by"),
                    text=comment_json.get("text"),
                    parent=parent,
                ),
                item_id=comment_id,
            )

        return (
            super().get_queryset().filter(parent_type=parent_type, parent_id=parent.pk)
        )

    def get_data(self, context):
        page = context["page_obj"]
        paginator = page.paginator

        (scheme, netloc, path, query, fragment) = parse.urlsplit(
            self.request.get_full_path()
        )
        query_dict = parse.parse_qs(query, keep_blank_values=True)

        next_query_dict = dict(query_dict)
        if page.has_next():
            next_query_dict[self.page_kwarg] = page.next_page_number()
            query = parse.urlencode(sorted(next_query_dict.items()), doseq=True)
            next_url = parse.urlunsplit((scheme, netloc, path, query, fragment))
        else:
            next_url = None

        comment_results = self._get_comment_results(context["object_list"])

        return {
            "page": page.number,
            "count": paginator.count,
            "next": next_url,
            "results": comment_results,
        }
