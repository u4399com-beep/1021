"""Book ratings (v80) — user ratings + aggregate."""
from __future__ import annotations
from django.db import models
from django.db.models import Avg


class BookRating(models.Model):
    """A reader's rating for a book (1-5 stars)."""
    reader = models.ForeignKey("account.ReaderProfile", on_delete=models.CASCADE, related_name="ratings")
    book = models.ForeignKey("novel.Book", on_delete=models.CASCADE, related_name="user_ratings")
    score = models.IntegerField("评分", help_text="1-5 星")
    review = models.TextField("书评", blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "novel_book_rating"
        verbose_name = "书籍评分"
        verbose_name_plural = verbose_name
        unique_together = ("reader", "book")
        ordering = ("-id",)

    def __str__(self): return f"{self.reader.username} → {self.book.title} ({self.score}★)"


def update_book_aggregate_rating(book):
    """Recalculate a book's aggregate rating from all user ratings."""
    avg = book.user_ratings.aggregate(Avg("score"))["score__avg"]
    book.rating = round(avg, 1) if avg else 0
    book.save(update_fields=["rating"])
    return book.rating
