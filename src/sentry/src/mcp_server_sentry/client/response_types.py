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


# --- Error types in latestEvent.errors ---
class ErrorData(TypedDict, total=False):
    column: int
    source: str
    row: int


class ErrorItem(TypedDict, total=False):
    message: str
    type: str
    data: ErrorData


# --- Metadata union ---
class MetadataA(TypedDict):
    type: str
    value: str


class MetadataB(TypedDict):
    title: str


Metadata = Union[MetadataA, MetadataB]


# --- Tag type ---
class Tag(TypedDict, total=False):
    value: str
    key: str
    _meta: Optional[str]


# --- User types ---
class UserData(TypedDict, total=False):
    isStaff: bool


class User(TypedDict):
    username: Optional[str]
    name: Optional[str]
    ip_address: Optional[str]
    email: Optional[str]
    data: Optional[UserData]
    id: str


# --- Entry types ---
# Entry Type 1: with data.values array
class EntryType1Value(TypedDict):
    category: str
    level: str
    event_id: Optional[str]
    timestamp: str  # ISO date-time string
    data: Optional[Dict[str, Any]]
    message: Optional[str]
    type: str


class EntryType1Data(TypedDict):
    values: List[EntryType1Value]


class EntryType1(TypedDict):
    type: str
    data: EntryType1Data


# Entry Type 2: with detailed request data
class EntryType2Data(TypedDict):
    fragment: Optional[str]
    cookies: Optional[List[List[str]]]  # array of string arrays; nullable
    inferredContentType: Optional[str]
    env: Optional[Dict[str, str]]  # e.g. {"ENV": "value"}
    headers: List[List[str]]
    url: str
    query: List[List[str]]
    data: Optional[Dict[str, Any]]
    method: Optional[str]


class EntryType2(TypedDict):
    type: str
    data: EntryType2Data


# Entry Type 3: with formatted message
class EntryType3Data(TypedDict):
    formatted: str


class EntryType3(TypedDict):
    type: str
    data: EntryType3Data


# Entry Type 4: with stacktrace information
class Frame(TypedDict):
    function: str
    errors: Optional[str]
    colNo: Optional[int]
    vars: Optional[Dict[str, Any]]
    package: Optional[str]
    absPath: Optional[str]
    inApp: bool
    lineNo: int
    module: str
    filename: str
    platform: Optional[str]
    instructionAddr: Optional[str]
    context: List[List[Union[int, str]]]
    symbolAddr: Optional[str]
    trust: Optional[str]
    symbol: Optional[str]


class EntryType4ValueStacktrace(TypedDict):
    frames: List[Frame]
    framesOmitted: Optional[str]
    registers: Optional[str]
    hasSystemFrames: bool


class EntryType4ValueMechanism(TypedDict):
    type: str
    handled: bool


class EntryType4Value(TypedDict):
    stacktrace: Optional[EntryType4ValueStacktrace]
    module: Optional[str]
    rawStacktrace: Optional[Dict[str, Any]]
    mechanism: Optional[EntryType4ValueMechanism]
    threadId: Optional[str]
    value: str
    type: str


class EntryType4Data(TypedDict):
    excOmitted: Optional[List[int]]
    hasSystemFrames: bool
    values: List[EntryType4Value]


class EntryType4(TypedDict):
    type: str
    data: EntryType4Data


Entry = Union[EntryType1, EntryType2, EntryType3, EntryType4]


# --- SDK ---
class Sdk(TypedDict):
    version: str
    name: str


# --- _meta ---
class Meta(TypedDict, total=False):
    user: Optional[str]
    context: Optional[str]
    entries: Dict[str, Any]
    contexts: Optional[str]
    message: Optional[str]
    packages: Optional[str]
    tags: Dict[str, Any]
    sdk: Optional[str]


# --- Contexts ---
class ResponseJSON(TypedDict):
    detail: str


class ForbiddenErrorContext(TypedDict):
    status: int
    statusText: str
    responseJSON: ResponseJSON
    type: str


class BrowserContext(TypedDict):
    version: str
    type: str
    name: str


class OSContext(TypedDict):
    version: str
    type: str
    name: str


class TraceContext(TypedDict):
    span_id: str
    type: str
    trace_id: str
    op: str


class OrganizationContext(TypedDict):
    type: str
    id: str
    slug: str


class Contexts(TypedDict, total=False):
    ForbiddenError: ForbiddenErrorContext
    browser: BrowserContext
    os: OSContext
    trace: TraceContext
    organization: OrganizationContext


# --- Context (singular) ---
class ContextRespResponseJSON(TypedDict):
    detail: str


class ContextResp(TypedDict):
    status: int
    responseJSON: ContextRespResponseJSON
    name: str
    statusText: str
    message: str
    stack: str


class ContextSession(TypedDict):
    foo: str


class ContextDetail(TypedDict):
    resp: ContextResp
    session: ContextSession
    unauthorized: bool
    url: str


# --- LatestEvent ---
class LatestEvent(TypedDict):
    eventID: str
    dist: Optional[str]
    message: str
    id: str
    size: int
    errors: List[ErrorItem]
    platform: str
    type: str
    metadata: Metadata
    tags: List[Tag]
    dateCreated: str
    dateReceived: str
    user: Optional[User]
    entries: List[Entry]
    packages: Dict[str, Any]
    sdk: Sdk
    _meta: Meta
    contexts: Contexts
    fingerprints: List[str]
    context: ContextDetail
    groupID: str
    title: str


class SentryIssueHash(TypedDict):
    latestEvent: LatestEvent
    id: str
