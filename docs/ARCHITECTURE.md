
## **1. Diagram**
```mermaid

flowchart TD
    subgraph CLIENT["Client Layer"]
        WEB["React PWA<br>(Web Browser)"]
        MOBILE["Expo App<br>(iOS / Android)"]
        MSG["Messaging Platforms<br>WhatsApp - Telegram - Messenger"]
    end

    subgraph GATEWAY["API Layer (AWS)"]
        APIGW_REST["API Gateway<br>REST — /chat - /sos - /documents - /alerts"]
        APIGW_WS["API Gateway<br>WebSocket — /voice stream"]
    end

    subgraph COMPUTE["Compute (AWS Lambda)"]
        ORCH["Orchestrator Agent<br>Strands Agents + Nova Lite<br>Intent detection - Agent routing"]
    end

    subgraph AGENTS["Agent Pool"]
        VOICE_AGT["Voice Agent<br>Nova Sonic<br>Speech-to-speech<br>multilingual"]
        DOC_AGT["Document Agent<br>Nova Pro Multimodal<br>Extract - Explain - Translate"]
        AID_AGT["Aid Locator Agent<br>Amazon Location Service<br>UNHCR - IOM APIs"]
        NEWS_AGT["News Intelligence Agent<br>Nova Lite<br>ReliefWeb - ACLED<br>Conflict alerts"]
        CRISIS_AGT["Crisis Routing Agent<br>Nova Lite<br>Urgency detection<br>Emergency report generation"]
    end

    subgraph DATA["Data Layer (AWS)"]
        DYNAMO["DynamoDB<br>Sessions - SOS records<br>Alert cache"]
        S3["S3<br>Uploaded documents<br>Audio buffers"]
        CACHE["ElastiCache<br>Session state<br>Voice context"]
    end

    subgraph NOTIFY["Notification Layer"]
        SNS["Amazon SNS<br>SOS push alerts<br>to emergency contacts"]
        EVENTBRIDGE["EventBridge<br>Scheduled news polling<br>every 15 minutes"]
    end

    subgraph EXTERNAL["External Data Sources"]
        UNHCR["UNHCR API<br>Camp locations"]
        RELIEFWEB["ReliefWeb API<br>Humanitarian news"]
        ACLED["ACLED API<br>Conflict events"]
        OSM["OpenStreetMap<br>Clinics - Water - Hospitals"]
    end

    subgraph AUTH["Auth"]
        COGNITO["Amazon Cognito<br>Guest + registered sessions"]
    end

    %% Client → Gateway
    WEB -->|HTTPS / WSS| APIGW_REST
    WEB -->|WSS| APIGW_WS
    MOBILE -->|HTTPS / WSS| APIGW_REST
    MOBILE -->|WSS| APIGW_WS
    MSG -->|Webhook| APIGW_REST

    %% Auth
    WEB & MOBILE --> COGNITO
    COGNITO --> APIGW_REST

    %% Gateway → Orchestrator
    APIGW_REST --> ORCH
    APIGW_WS --> VOICE_AGT

    %% Orchestrator → Agents
    ORCH --> VOICE_AGT
    ORCH --> DOC_AGT
    ORCH --> AID_AGT
    ORCH --> NEWS_AGT
    ORCH --> CRISIS_AGT

    %% Agents → Data
    ORCH --> DYNAMO
    DOC_AGT --> S3
    VOICE_AGT --> CACHE
    CRISIS_AGT --> DYNAMO

    %% Agents → External
    AID_AGT --> UNHCR
    AID_AGT --> OSM
    NEWS_AGT --> RELIEFWEB
    NEWS_AGT --> ACLED

    %% Notifications
    CRISIS_AGT --> SNS
    EVENTBRIDGE --> NEWS_AGT

    %% Styling
    classDef aws fill:#FF9900,color:#000,stroke:#FF9900
    classDef nova fill:#232F3E,color:#fff,stroke:#FF9900
    classDef client fill:#0073BB,color:#fff,stroke:#0073BB
    classDef external fill:#2ea44f,color:#fff,stroke:#2ea44f

    class APIGW_REST,APIGW_WS,DYNAMO,S3,SNS,EVENTBRIDGE,COGNITO,CACHE aws
    class VOICE_AGT,DOC_AGT,NEWS_AGT,CRISIS_AGT,ORCH nova
    class WEB,MOBILE,MSG client
    class UNHCR,RELIEFWEB,ACLED,OSM external

```

## **2. Costs**
**Total Hackathon Cost: ~$14**

|AWS Service|Hackathon Cost|Why|
|---|---|---|
|**Amazon Nova Sonic**|~$3.00|~60 min of demo voice sessions @ $0.017/min blended|
|**Amazon Nova Lite**|~$1.50|Orchestrator + chat tokens (~2M tokens @ $0.06/1M in + $0.24/1M out)|
|**Amazon Nova Pro**|~$0.50|~50 document uploads for testing|
|**API Gateway (WebSocket)**|~$1.00|Voice streaming sessions|
|**Amazon Location Service**|~$0.25|~500 aid center proximity queries|
|**Amazon SNS**|~$0.08|~100 SOS test alerts|
|**Amazon S3**|~$0.02|Document uploads (<1GB)|
|**Contingency buffer**|~$1.00|10%|
|**Lambda, DynamoDB, Cognito, CloudWatch, API Gateway REST**|$0.00|All covered by AWS free tier|
|**UNHCR, ReliefWeb, ACLED, OpenStreetMap APIs**|$0.00|Free for humanitarian use|

**The big takeaway:** Nova Sonic is probably only real spend at ~$3, and that's for 60 minutes of voice testing. If we keep demo voice sessions short (under 5 min each), we could run the entire hackathon for under $10. The free tier absorbs almost everything else.
