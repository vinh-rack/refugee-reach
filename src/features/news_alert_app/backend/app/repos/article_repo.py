import uuid

from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.enums import ArticleStatus

def get_article_by_source_external_id(db: Session, source_id: str, external_id: str) -> Article | None:
    return (
        db.query(Article)
        .filter(Article.source_id == source_id, Article.external_id == external_id)
        .first()
    )
    
def create_article(db: Session, **kwargs) -> Article:
    article = Article(**kwargs)
    db.add(article)
    db.flush()
    return article


def get_article_by_id(db: Session, article_id: uuid.UUID) -> Article | None:
    return db.get(Article, article_id)


def list_articles_by_status(
    db: Session,
    status: ArticleStatus,
    limit: int = 500,
) -> list[Article]:
    return (
        db.query(Article)
        .filter(Article.status == status)
        .order_by(Article.created_at.asc())
        .limit(limit)
        .all()
    )


def find_duplicate_by_normalized_hash(
    db: Session,
    *,
    normalized_hash: str | None,
    exclude_article_id: uuid.UUID,
) -> Article | None:
    if not normalized_hash:
        return None
    return (
        db.query(Article)
        .filter(
            Article.normalized_hash == normalized_hash,
            Article.id != exclude_article_id,
            Article.status != ArticleStatus.REJECTED,
        )
        .order_by(Article.created_at.asc())
        .first()
    )


def find_duplicate_by_url(
    db: Session,
    *,
    url: str | None,
    exclude_article_id: uuid.UUID,
) -> Article | None:
    if not url:
        return None
    return (
        db.query(Article)
        .filter(
            Article.url == url,
            Article.id != exclude_article_id,
            Article.status != ArticleStatus.REJECTED,
        )
        .order_by(Article.created_at.asc())
        .first()
    )
