from app.schemas.dns_event import DnsEventSchema, DnsEventCreate
from app.schemas.recommendation import RecommendationSchema, RecommendationUpdate
from app.schemas.dependency import DependencySchema
from app.schemas.client_profile import ClientProfileSchema
from app.schemas.fqdn_profile import FqdnProfileSchema

__all__ = [
    "DnsEventSchema",
    "DnsEventCreate",
    "RecommendationSchema",
    "RecommendationUpdate",
    "DependencySchema",
    "ClientProfileSchema",
    "FqdnProfileSchema",
]
