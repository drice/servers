from typing import TypedDict, List, Optional, Union, Dict, Any


class Team(TypedDict):
    id: str
    name: str
    slug: str


class EventProcessing(TypedDict):
    symbolicationDegraded: bool


class LatestRelease(TypedDict):
    version: str


class SentryProject(TypedDict):
    latestDeploys: Optional[Dict[str, Dict[str, str]]]
    options: Dict[str, Any]
    stats: Dict[str, Any]
    transactionStats: Dict[str, Any]
    sessionStats: Dict[str, Any]
    id: str
    slug: str
    name: str
    platform: Optional[str]
    dateCreated: str
    isBookmarked: bool
    isMember: bool
    features: List[str]
    firstEvent: Optional[str]
    firstTransactionEvent: bool
    access: List[str]
    hasAccess: bool
    hasFeedbacks: bool
    hasFlags: bool
    hasMinifiedStackTrace: bool
    hasMonitors: bool
    hasNewFeedbacks: bool
    hasProfiles: bool
    hasReplays: bool
    hasSessions: bool
    hasInsightsHttp: bool
    hasInsightsDb: bool
    hasInsightsAssets: bool
    hasInsightsAppStart: bool
    hasInsightsScreenLoad: bool
    hasInsightsVitals: bool
    hasInsightsCaches: bool
    hasInsightsQueues: bool
    hasInsightsLlmMonitoring: bool
    team: Optional[Team]
    teams: List[Team]
    eventProcessing: EventProcessing
    platforms: List[str]
    hasUserReports: bool
    environments: List[str]
    latestRelease: Optional[LatestRelease]
