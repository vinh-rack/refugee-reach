# RefugeeReach - AI Emergency Companion for Displaced People

Most winning projects are usually ***multi-modal and multi-agent*** projects, with themes relevant to real, recent world events that have an effect on people, notable themes include:
- Environment
- Finance
- Geopolitical conflicts:
	- Iran vs US
	- Gaza

What kind of project can we make from these ideas?

---

## **1. Project Overview**
**RefugeeReach** is a multilingual, voice-first AI assistant designed to help displaced people navigate crisis situations. The system uses Amazon Nova models to provide real-time voice interaction, document understanding, verified aid discovery, and emergency escalation.

The platform is designed for **low-literacy, high-stress environments** where users may not understand the local language or legal processes. It works via a web application and can also integrate into messaging and social media platforms so users can access assistance from familiar communication channels.

**RefugeeReach** combines three major capabilities:
- Voice-based crisis assistance
- Multimodal document understanding
- Verified aid and emergency routing

Additionally, the platform includes a **news intelligence and alert feed** that monitors reliable sources and notifies users about urgent developments such as border closures, escalating conflict, or evacuation warnings.

## **2. Problem Statement**
Millions of displaced people face immediate challenges after fleeing conflict zones:
- Language barriers when interacting with aid organizations
- Difficulty understanding official documents
- Lack of reliable information about safe shelters or aid services
- Limited access to trustworthy updates about security conditions
- Inability to communicate emergency needs effectively

Existing tools often focus on translation only. They do not provide structured guidance, contextual understanding, or emergency routing.

**RefugeeReach** aims to fill this gap by acting as a **trusted digital companion during displacement**.

## **3. Core Goals**
1. Enable displaced people to **ask for help in their own language**.
2. Help users **understand documents and instructions** from authorities.
3. Provide **verified nearby aid resources**.
4. Detect and escalate **urgent crisis situations**.
5. Deliver **reliable alerts about dangerous developments**.
6. Work across **web and social messaging platforms**.

## **4. Key Features**
1. **SOS Button**: One tap broadcasts the user's live GPS location to registered emergency contacts and nearby rescue volunteers via a shareable map link.
2. **Voice Agent**: Speak in any supported language; an orchestrator agent routes the request to specialized sub-agents (refugee camp locator, news & border status, legal rights, medical triage).
3. **Chat Agent**: Text-based access to the same agent system, with support for document photo uploads that are read and explained by a multimodal Nova agent.
4. **Cross-platform**: Works on iOS, Android, and web browsers with a single codebase, optimized for low-bandwidth conditions.

More details below.

### *4.1. Multilingual Voice Assistant*
A real-time voice in English, Arabic, Farsi, Hebrew allowing users to communicate naturally.

Capabilities:
- Speech-to-speech multilingual interaction
- Support for languages common in crisis zones
- Conversational question answering
- Context-aware responses

Example interaction:
1. User: "I crossed the border yesterday and I don't know where to go."
2. Assistant:
	- asks follow-up questions
	- identifies user needs
	- recommends nearby aid centers

Voice interaction is designed to reduce friction for users with low literacy.

### *4.2. Aid Resource Finder*
Search and recommendation of verified aid services **near the user's location** such as:
- shelters
- food distribution
- water stations
- medical clinics
- legal aid

Data sources may include organizations like:
- UNHCR
- Red Cross/Red Crescent
- International Organization for Migration
- local NGOs

The system prioritizes **trusted sources** and clearly displays the origin of information.

### *4.3. Crisis Detection and Escalation*
Detecting urgent situations through UI button or agent understanding.

> basically like an SOS button

Examples:
- injury
- missing family members
- lack of water
- violence or immediate danger

If detected or prompted through UI button or user input through voice or chat, the system:
1. collects structured information
2. generates a concise emergency summary
3. routes the information to available support channels

Collected data may include:
- number of people
- injuries
- location
- urgent needs

This helps convert unstructured voice messages into **actionable information for responders**.

### *4.4. Document Understanding Agent*
Users can upload photos or scans of documents.

The system extracts and explains:
- registration notices
- asylum paperwork
- aid distribution instructions
- medical forms

Output includes:
- simple explanation
- deadlines
- required actions
- spoken summary in the user's language

Example:
"This document says you must register at the city office before Friday. Bring identification if available."

### *4.5. War and Safety Alert Feed (News Finder)*
To help users stay informed, **RefugeeReach** includes a **news intelligence system**.

> This was taken inspiration from [World Monitor](https://world-monitor.com).

This feature monitors trusted information sources and provides alerts about critical developments.

Possible alerts:
- border closures
- evacuation warnings
- escalating conflict nearby
- aid distribution announcements

Sources may include:
- international news agencies
- humanitarian organizations
- government announcements

The system filters and summarizes information to prevent misinformation.

Users receive notifications through:
- web interface
- messaging apps
- social media integrations

Each alert includes:
- short explanation
- source
- recommended action if relevant

### *4.6 Social Media and Messaging Integration*
To make the system accessible, **RefugeeReach** can integrate with platforms such as:
- WhatsApp
- Telegram
- Messenger
- other messaging systems

Users can interact with the assistant through chat or voice messages.

Benefits:
- no need to install a new app
- familiar communication channels
- easier adoption
## **5. System Architecture**
The platform is structured as a multi-agent system.
### *5.1 Conversation Agent*
Responsibilities:
- voice interaction
- intent detection
- conversation management

### *5.2 Crisis Routing Agent*
Responsibilities:
- urgency detection
- structured information extraction
- aid recommendation

### *5.3 News Intelligence Agent*
Responsibilities:
- monitoring trusted sources
- filtering critical updates
- generating alerts

### *5.4 Document Analysis Agent (maybe)* 
Responsibilities:
- image and document processing
- text extraction
- explanation generation

### *5.5 Orchestrator*
Coordinates interactions between agents and selects the correct workflow.

## **6. Technology Stack**
Refer to **[Tech Stack document](STACK.md)** for more details.

- AI Models:
	- Amazon Nova Sonic for voice interaction
	- Amazon Nova multimodal models for document analysis
- Infrastructure:
	- cloud-based API services
	- web frontend
	- messaging platform integrations
- Data Sources:
	- humanitarian organization APIs
	- curated NGO datasets
	- trusted news feeds

## **7. Demo Scenario (Hackathon)**
A short demonstration flow:
1. A user speaks Arabic asking for help.
2. The assistant responds and recommends nearby shelter.
3. The user uploads a photo of a registration document.
4. The system explains the document in simple language.
5. The system shows an alert from the news feed warning about nearby conflict.
6. The assistant detects an urgent situation and prepares an emergency report.

## **8. Impact**
**RefugeeReach** aims to:
- improve access to reliable information
- reduce confusion around official processes
- help people find assistance faster
- enable more effective communication during emergencies

In crisis situations, even small pieces of information can significantly improve safety and decision-making.
