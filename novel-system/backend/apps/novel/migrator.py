"""Data migration tool (v75) — import data from other novel systems."""
import json


def import_books_from_json(json_data: list[dict] | str, overwrite: bool = False) -> dict:
    """Import books from a JSON array.
    
    Each book dict: {title, author, intro, cover_url, source_url, categories, chapters}
    chapters: [{title, content, order_index, source_url}]
    """
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    
    from apps.novel.models import Book, Author, Chapter, Category
    imported, skipped, errors = 0, 0, []
    
    for item in json_data:
        try:
            title = item.get("title", "").strip()
            if not title:
                errors.append({"error": "missing title"})
                continue
            
            author_name = item.get("author", "").strip() or "佚名"
            author, _ = Author.objects.get_or_create(name=author_name)
            
            book, created = Book.objects.update_or_create(
                source_url=item.get("source_url", ""),
                defaults={
                    "title": title, "author": author,
                    "intro": item.get("intro", ""),
                    "cover_url": item.get("cover_url", ""),
                },
            )
            if not created and not overwrite:
                skipped += 1
                continue
            
            # Categories
            for cat_name in item.get("categories", []):
                cat, _ = Category.objects.get_or_create(name=cat_name, defaults={"slug": cat_name})
                book.categories.add(cat)
            
            # Chapters
            for ch_data in item.get("chapters", []):
                Chapter.objects.update_or_create(
                    book=book, source_url=ch_data.get("source_url", ""),
                    defaults={
                        "title": ch_data.get("title", ""),
                        "order_index": ch_data.get("order_index", 0),
                        "content": ch_data.get("content", ""),
                        "word_count": len(ch_data.get("content", "")),
                        "status": "published",
                    },
                )
            
            book.chapter_count = book.chapters.count()
            book.save(update_fields=["chapter_count"])
            imported += 1
        except Exception as e:
            errors.append({"error": repr(e), "title": item.get("title", "?")})
    
    return {"imported": imported, "skipped": skipped, "errors": errors}


def import_from_csv_format(rows: list[dict]) -> dict:
    """Import from CSV-like rows (title, author, intro, source_url)."""
    return import_books_from_json(rows)
