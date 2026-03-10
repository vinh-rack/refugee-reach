# Tech Stack

## **1. Frontend**

| Layer           | Technology                               | Purpose                         |
| --------------- | ---------------------------------------- | ------------------------------- |
| Web App         | React + Vite                             | Main web PWA                    |
| Mobile          | Expo (React Native)                      | iOS + Android                   |
| Shared UI       | Tailwind CSS + shadcn/ui                 | Shared component library        |
| Realtime Audio  | WebSocket (browser/native)               | Voice streaming to Nova Sonic   |
| Offline Support | Service Workers + IndexedDB              | Cached phrases, queued messages |
| Maps            | Amazon Location Service (MapLibre GL JS) | Aid center map rendering        |

## **2. Backend**

| Layer                | Technology                         | Purpose                                       |
| -------------------- | ---------------------------------- | --------------------------------------------- |
| API Layer            | AWS API Gateway (REST + WebSocket) | REST for chat/SOS, WS for voice               |
| Compute              | AWS Lambda (Python 3.12)           | Serverless function handlers                  |
| Orchestration        | Strands Agents (Python)            | Multi-agent coordination                      |
| Auth                 | Amazon Cognito                     | User identity, anonymous guest sessions       |
| Database             | Amazon DynamoDB                    | Sessions, SOS records, alert cache            |
| File Storage         | Amazon S3                          | Uploaded documents and images                 |
| Push Notifications   | Amazon SNS                         | SOS alerts to emergency contacts              |
| Translation Fallback | Amazon Translate                   | Languages outside Nova Sonic's native support |
| News Ingestion       | AWS EventBridge + Lambda           | Scheduled news polling pipeline               |

---

## AI / ML (Amazon Nova)
| Model | Usage |
|---|---|
| Amazon Nova Sonic | Real-time speech-to-speech voice assistant |
| Amazon Nova Lite | Orchestrator reasoning, chat, crisis detection, news summarization |
| Amazon Nova Pro (multimodal) | Document photo understanding and extraction |

---

## Agents (Strands Agents Framework)
| Agent | Responsibility |
|---|---|
| Orchestrator | Intent classification, agent routing, conversation state |
| Voice Agent | Wraps Nova Sonic stream, manages turn-taking |
| Document Agent | Receives S3 image URL, calls Nova Pro multimodal, returns plain-language summary |
| Aid Locator Agent | Queries Amazon Location Service + UNHCR/IOM APIs for nearby resources |
| News Intelligence Agent | Polls trusted feeds, filters by relevance and geography, generates alerts |
| Crisis Routing Agent | Detects urgency signals, structures emergency report, triggers SNS SOS |

---

## External Data Sources
| Source | Data |
|---|---|
| UNHCR API | Registered camps, displacement statistics |
| ReliefWeb API | Humanitarian news and alerts |
| ACLED API | Conflict event data and locations |
| OpenStreetMap (Overpass) | Hospitals, clinics, water points |
| Google Maps Places API (fallback) | Additional POI coverage |

---

## DevOps & Infrastructure
| Tool | Purpose |
|---|---|
| AWS CDK (Python) | Infrastructure as code |
| GitHub Actions | CI/CD pipeline |
| AWS CloudWatch | Logging and monitoring |
| AWS WAF | API protection |
| Sentry | Frontend error tracking |

---

## Messaging Integrations (Phase 2)
| Platform | Method |
|---|---|
| WhatsApp | WhatsApp Business Cloud API |
| Telegram | Telegram Bot API |
| Messenger | Meta Webhooks |

---

## Cost-Sensitive Design Decisions
- Lambda + DynamoDB = scales to zero between hackathon demos
- Nova Lite used for all text/reasoning (cheapest Nova model)
- Nova Pro multimodal called only on document upload (not every message)
- Nova Sonic sessions capped at 5 minutes per voice interaction
- S3 lifecycle policy deletes uploaded documents after 24 hours
