from typing import TypedDict, List, Optional, Union, Dict, Any, Literal


class MetadataFile(TypedDict):
    filename: str
    type: str
    value: str


class MetadataException(TypedDict):
    title: str


Metadata = Union[MetadataFile, MetadataException]


class Project(TypedDict, total=False):
    id: str
    name: str
    slug: str


# For "stats", note the key "24h" is not a valid Python identifier,
# so we use the functional syntax to create the TypedDict.
Stats = TypedDict("Stats", {"24h": List[List[float]]})


class SentryIssue(TypedDict):
    annotations: List[str]
    assignedTo: Optional[Dict[str, Any]]  # no further structure specified
    count: str
    culprit: str
    firstSeen: str
    hasSeen: bool
    id: str
    isBookmarked: bool
    isPublic: bool
    isSubscribed: bool
    lastSeen: str
    level: str
    logger: Optional[str]
    metadata: Metadata
    numComments: int
    permalink: str
    project: Project
    shareId: Optional[str]
    shortId: str
    stats: Stats
    status: Literal["resolved", "unresolved", "ignored"]
    statusDetails: Dict[str, Any]
    subscriptionDetails: Optional[Dict[str, Any]]
    title: str
    type: str
    userCount: int
