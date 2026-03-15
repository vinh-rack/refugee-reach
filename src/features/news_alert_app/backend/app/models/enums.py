import enum


class SourceType(str, enum.Enum):
    RSS = "rss"
    API = "api"
    WEBSITE = "website"
    SOCIAL = "social"
    GOVERNMENT = "government"
    OTHER = "other"


class TrustTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class ArticleStatus(str, enum.Enum):
    INGESTED = "ingested"
    NORMALIZED = "normalized"
    CLUSTERED = "clustered"
    ANALYZED = "analyzed"
    REJECTED = "rejected"


class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    RETRYING = "retrying"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"