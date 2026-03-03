# A2A-Architektur: Komponenten, Protokoll und Scopes

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Schichtenarchitektur](#schichtenarchitektur)
3. [Komponenten und Separation of Concerns](#komponenten-und-separation-of-concerns)
4. [Scopes](#scopes)
5. [Protokoll](#protokoll)
6. [Datenmodell](#datenmodell)
7. [JSON-RPC Methoden](#json-rpc-methoden)
8. [Multi-Agent-Architektur](#multi-agent-architektur)

---

## Überblick

Das A2A-Protokoll (Agent-to-Agent) definiert eine standardisierte, technologieneutrale Kommunikation zwischen autonomen Agenten. Es ermöglicht Agenten — unabhängig von Programmiersprache, Framework oder LLM-Provider — sich gegenseitig zu entdecken, Fähigkeiten auszutauschen und Aufgaben zu delegieren.

### Kernprinzipien

| Prinzip | Beschreibung |
|---|---|
| **Interoperabilität** | Jeder A2A-konforme Agent kann mit jedem anderen kommunizieren (Spring AI, Python, TypeScript, ...) |
| **Discovery-First** | Agenten veröffentlichen ihre Fähigkeiten über eine AgentCard, bevor Kommunikation stattfindet |
| **Aufgabenorientiert** | Kommunikation ist um Tasks organisiert, nicht um einfache Request/Response-Paare |
| **Zustandsbehaftet** | Tasks durchlaufen einen definierten Lebenszyklus mit nachvollziehbaren Zustandsübergängen |
| **Multimodal** | Messages und Artifacts können Text, Dateien und strukturierte Daten enthalten |

---

## Schichtenarchitektur

Das Protokoll ist in vier klar getrennte Schichten gegliedert. Jede Schicht hat eine definierte Verantwortlichkeit und ist unabhängig austauschbar.

```
+==========================================================================+
|                        APPLICATION LAYER                                 |
|  Business Logic  |  State Management  |  Skills  |  Plugin Extensions    |
+==========================================================================+
|                         PROTOCOL LAYER                                   |
|  AgentCard Discovery  |  Task Routing  |  Flow Control  |  Error Handling|
+==========================================================================+
|                          MESSAGE LAYER                                   |
|  JSON-RPC Encoding  |  Serialization  |  Message/Artifact/Part Schema    |
+==========================================================================+
|                         TRANSPORT LAYER                                  |
|  HTTP/HTTPS  |  WebSocket  |  Server-Sent Events (SSE)                   |
+==========================================================================+
```

### Aufgaben der Schichten

| Schicht | Aufgabe | Separation of Concern |
|---|---|---|
| **Transport** | Netzwerkkommunikation und Verbindungsmanagement | WIE werden Bytes übertragen? |
| **Message** | Serialisierung, Schema-Validierung, Nachrichtenformat | WIE werden Daten strukturiert? |
| **Protocol** | Discovery, Task-Routing, Zustandsübergänge, Fehlerbehandlung | WELCHE Regeln gelten für die Kommunikation? |
| **Application** | Fachlogik, Skills, LLM-Interaktion, Tool-Aufrufe | WAS tut der Agent inhaltlich? |

---

## Komponenten und Separation of Concerns

### Komponentenübersicht

```
+---------------------------+                +---------------------------+
|      A2A CLIENT           |                |      A2A SERVER           |
+---------------------------+                +---------------------------+
|                           |   Discovery    |                           |
|  +---------------------+  |  GET /agent-   |  +---------------------+  |
|  | Client Application  |  |  card.json     |  | AgentCard Endpoint  |  |
|  +----------+----------+  +--------------->|  +---------------------+  |
|             |             |                |                           |
|  +----------v----------+  |  JSON-RPC      |  +---------------------+  |
|  | A2A Client SDK      |  |  sendMessage   |  | Message Controller  |  |
|  | - AgentCard Cache   +------------------>|  +----------+----------+  |
|  | - Task Management   |  |                |             |             |
|  | - Session Handling  |  |                |  +----------v----------+  |
|  +---------------------+  |                |  | Agent Executor      |  |
|                           |                |  +----------+----------+  |
|                           |                |             |             |
|                           |   Response     |  +----------v----------+  |
|                           |<---------------+  | ChatClient + Tools  |  |
|                           |   (Task mit    |  | - MCP Integration   |  |
|                           |    Artifacts)  |  | - LLM Model         |  |
|                           |                |  +---------------------+  |
+---------------------------+                +---------------------------+
```

### Client-Komponenten

| Komponente | Aufgabe | Scope |
|---|---|---|
| **Client Application** | Geschäftslogik, die den Agenten aufruft (UI, CLI, anderer Agent) | Anwendungsschicht |
| **A2A Client SDK** | Protokollkonformes Senden und Empfangen von Nachrichten | Protokollschicht |
| **AgentCard Cache** | Zwischenspeicherung entdeckter AgentCards, vermeidet wiederholte Discovery-Aufrufe | Protokollschicht |
| **Task Management** | Verwaltung laufender Tasks (Status-Polling, Abbruch, Resubscribe) | Protokollschicht |
| **Session Handling** | Zuordnung von Tasks zu Sessions für zusammenhängende Konversationen | Protokollschicht |

### Server-Komponenten

| Komponente | Aufgabe | Scope |
|---|---|---|
| **AgentCard Endpoint** | Bereitstellung der AgentCard unter `/.well-known/agent-card.json` | Protocol Layer — Discovery |
| **Message Controller** | Empfang und Routing von JSON-RPC-Nachrichten (message/send, tasks/get, tasks/cancel) | Protocol Layer — Routing |
| **Agent Executor** | Orchestrierung: Empfang der Anfrage, Delegation an den ChatClient, Zustandsverwaltung des Tasks | Protocol/Application Layer — Brücke |
| **ChatClient** | LLM-Interaktion: Prompt-Aufbau, Tool-Aufrufe, Antwortgenerierung | Application Layer |
| **Tools / Skills** | Fachliche Operationen (Datenbankabfragen, API-Aufrufe, Berechnungen) | Application Layer |
| **MCP Integration** | Bereitstellung und Nutzung von Tools über das Model Context Protocol | Application Layer |
| **Task Store** | Persistierung von Task-Zuständen, Artifacts und History | Protocol Layer — State |

### Separation of Concerns

```
Verantwortlichkeit         Wer ist zuständig?           Wer ist NICHT zuständig?
─────────────────────────  ───────────────────────────   ───────────────────────────
Discovery & Identität      AgentCard Endpoint            Agent Executor
Nachrichtenempfang         Message Controller            ChatClient
Task-Zustandsmaschine      Agent Executor + TaskStore    Tools / Skills
LLM-Interaktion            ChatClient                    Message Controller
Fachlogik                  Tools / Skills                Agent Executor
Datenhaltung               TaskStore                     Message Controller
Fehlerbehandlung           Jede Schicht für ihre Ebene   Nicht schichtübergreifend
```

**Wichtig**: Der Agent Executor ist die zentrale Brücke zwischen Protokoll- und Anwendungsschicht. Er übersetzt A2A-Nachrichten in ChatClient-Aufrufe und ChatClient-Antworten zurück in A2A-Tasks. Er enthält selbst keine Fachlogik.

---

## Scopes

Das A2A-Protokoll definiert verschiedene Geltungsbereiche (Scopes), die bestimmen, wie Zustand, Kontext und Identität organisiert sind.

### 1. Agent Scope

Der Agent als Ganzes: seine Identität, Fähigkeiten und öffentliche Schnittstelle.

```
Agent Scope
+-----------------------------------------------------------------------+
| AgentCard                                                             |
|   - Name, Description, Version                                       |
|   - URL (Erreichbarkeit)                                              |
|   - Skills (Fähigkeiten)                                              |
|   - Capabilities (Streaming, Push, History)                           |
|   - Authentication (optional)                                         |
+-----------------------------------------------------------------------+
```

- **Lebensdauer**: So lange der Agent-Server läuft
- **Sichtbarkeit**: Öffentlich, für alle Clients über Discovery erreichbar
- **Zustand**: Stateless — die AgentCard ändert sich nicht zur Laufzeit

### 2. Session Scope

Eine Sitzung gruppiert zusammengehörende Tasks zu einer Konversation.

```
Session Scope (sessionId: "abc-123")
+-----------------------------------------------------------------------+
| Task 1: "Zeige Kategorien"          → completed                      |
| Task 2: "Wähle Reisepass"           → completed                      |
| Task 3: "Suche in Bürgeramt Mitte"  → completed                      |
+-----------------------------------------------------------------------+
| Conversation History (pro Session)                                    |
|   [UserMessage, AssistantMessage, UserMessage, AssistantMessage, ...] |
+-----------------------------------------------------------------------+
```

- **Lebensdauer**: Wird vom Client durch die `sessionId` gesteuert
- **Sichtbarkeit**: Nur innerhalb der Kommunikation zwischen einem Client und einem Server
- **Zustand**: Stateful — enthält den Verlauf aller Nachrichten und Tasks

### 3. Task Scope

Ein einzelner Auftrag mit eigenem Lebenszyklus.

```
Task Scope (taskId: "task-001")
+-----------------------------------------------------------------------+
| Status: submitted → working → completed                               |
| Message (Eingabe): "Zeige alle Kategorien"                            |
| Artifacts (Ergebnis): [{TextPart: "Kategorien: ..."}]                 |
| History: [UserMessage, AgentMessage]                                  |
+-----------------------------------------------------------------------+
```

- **Lebensdauer**: Von `submitted` bis zu einem finalen Zustand (`completed`, `failed`, `canceled`)
- **Sichtbarkeit**: Über `tasks/get` abrufbar
- **Zustand**: Stateful — durchläuft eine definierte Zustandsmaschine

### 4. Message Scope

Eine einzelne Nachricht innerhalb eines Tasks.

```
Message Scope
+-----------------------------------------------------------------------+
| role: "user" | "agent"                                                |
| parts: [TextPart, DataPart, FilePart, ...]                           |
| metadata: { ... }                                                     |
+-----------------------------------------------------------------------+
```

- **Lebensdauer**: Immutable nach Erstellung
- **Sichtbarkeit**: Teil der Task-History
- **Zustand**: Stateless — eine Message wird nicht verändert

### Scope-Hierarchie

```
Agent Scope
  └── Session Scope (1:n)
        └── Task Scope (1:n)
              ├── Message Scope (1:n) — in history[]
              └── Artifact Scope (1:n) — in artifacts[]
```

---

## Protokoll

### Vollständiger Request-Response-Zyklus

Das Protokoll besteht aus fünf Kernschritten:

```
Client                          Server                         LLM/Tools
  |                               |                               |
  |  1. GET /.well-known/         |                               |
  |     agent-card.json           |                               |
  +------------------------------>|                               |
  |                               |                               |
  |  AgentCard (JSON)             |                               |
  |<------------------------------+                               |
  |                               |                               |
  |  [Client wertet Skills,       |                               |
  |   Capabilities und Auth aus]  |                               |
  |                               |                               |
  |  2. JSON-RPC POST             |                               |
  |     method: "message/send"    |                               |
  |     params: TaskSendParams    |                               |
  |       - id, sessionId         |                               |
  |       - message (Parts)       |                               |
  +------------------------------>|                               |
  |                               |                               |
  |                               |  3. AgentExecutor             |
  |                               |     execute(request)          |
  |                               +------------------------------>|
  |                               |                               |
  |                               |  4. ChatClient                |
  |                               |     prompt + tools            |
  |                               |     aufrufen                  |
  |                               |<------------------------------+
  |                               |                               |
  |                               |  [Optional: Tool Calls        |
  |                               |   MCP, REST, DB, ...]         |
  |                               +------------------------------>|
  |                               |<------------------------------+
  |                               |                               |
  |  5. JSON-RPC Response         |                               |
  |     Task {                    |                               |
  |       status: "completed"     |                               |
  |       artifacts: [...]        |                               |
  |       history: [...]          |                               |
  |     }                         |                               |
  |<------------------------------+                               |
  |                               |                               |
```

### Schritt 1: Agent Discovery

Bevor der Client eine Nachricht senden kann, muss er die Fähigkeiten des Servers kennen.

Der Client ruft die Well-Known URL ab:
```
GET /.well-known/agent-card.json
```

Die AgentCard enthält:
- **Identität**: Name, Description, Version, URL
- **Fähigkeiten (Skills)**: Was kann der Agent? Mit Beispiel-Prompts und Tags
- **Capabilities**: Streaming, Push-Notifications, State Transition History
- **Input/Output Modes**: Welche Datentypen werden akzeptiert und geliefert?
- **Authentication**: Welche Auth-Verfahren sind erforderlich? (optional)

Discovery-Strategien:
- **Well-Known URL**: Standardpfad `/.well-known/agent-card.json`
- **Registry**: Zentrales oder dezentrales Agentenverzeichnis
- **Manuell**: Direkte Konfiguration der AgentCard-URL

### Schritt 2: Request Reception

Der Client sendet eine JSON-RPC-2.0-Nachricht:

```
POST /
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "id": "task-001",
    "sessionId": "session-abc",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "Welche Kategorien gibt es?" }]
    }
  }
}
```

Der Message Controller empfängt die Nachricht, validiert das JSON-RPC-Format und erstellt einen Request Context.

### Schritt 3: Execution

Der Message Controller delegiert an den Agent Executor:
- **Task anlegen**: Status → `submitted`
- **Arbeit beginnen**: Status → `working`
- **ChatClient aufrufen**: Prompt mit Conversation History und Tools zusammenstellen

### Schritt 4: Handler Invocation

Der ChatClient führt die eigentliche LLM-Interaktion aus:
- System-Prompt und Conversation History zusammenstellen
- LLM-Aufruf mit registrierten Tools
- Optional: Iterative Tool Calls (das LLM kann mehrere Tools nacheinander aufrufen)
- Antwort generieren

### Schritt 5: Response

Die Antwort wird in ein A2A-konformes Response-Objekt verpackt:
- **Task-Status**: `completed`, `failed` oder `input-required`
- **Artifacts**: Die eigentlichen Ergebnisse (Text, Daten, Dateien)
- **History**: Der Nachrichtenverlauf (optional, je nach Capabilities)

### Task-Lebenszyklus

```
                        +-------------+
                        |  submitted  |
                        +------+------+
                               |
                               v
                        +------+------+
              +-------->|   working   |<--------+
              |         +------+------+         |
              |                |                |
              |        +-------+-------+        |
              |        |       |       |        |
              v        v       v       v        |
       +------+--+ +---+---+ ++------++ +------+--------+
       | input-  | |comple-| |failed  | |   canceled    |
       | required| |ted    | |        | |               |
       +---------+ +-------+ +-------+ +---------------+
              |
              | (Client sendet
              |  weitere Daten)
              |
              +-----> zurück zu "working"
```

| Zustand | Beschreibung | Final? |
|---|---|---|
| `submitted` | Task wurde eingereicht, wartet auf Verarbeitung | Nein |
| `working` | Agent arbeitet aktiv an der Aufgabe | Nein |
| `input-required` | Agent benötigt weitere Eingaben vom Client | Nein |
| `completed` | Erfolgreich abgeschlossen | Ja |
| `failed` | Fehler bei der Ausführung | Ja |
| `canceled` | Vom Client abgebrochen | Ja |

---

## Datenmodell

### AgentCard

Die "Visitenkarte" eines Agenten. Wird als JSON unter `/.well-known/agent-card.json` bereitgestellt.

```
AgentCard
+-----------------------------------------------------------------------+
| name             : string        # Name des Agenten                   |
| description      : string        # Beschreibung                       |
| url              : string        # Service-URL des Agenten            |
| version          : string        # Versionsnummer                     |
| protocolVersion  : string        # A2A-Protokollversion (z.B. 0.2.1)  |
+-----------------------------------------------------------------------+
| capabilities                                                          |
|   +---------------------------------------------------------------+   |
|   | streaming              : boolean  # Streaming-Support         |   |
|   | pushNotifications      : boolean  # Push-Benachrichtigungen   |   |
|   | stateTransitionHistory : boolean  # Zustandshistorie          |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
| defaultInputModes  : string[]    # z.B. ["text"]                      |
| defaultOutputModes : string[]    # z.B. ["text", "data"]              |
+-----------------------------------------------------------------------+
| skills : Skill[]                                                      |
|   +---------------------------------------------------------------+   |
|   | id          : string      # Eindeutige Skill-ID               |   |
|   | name        : string      # Anzeigename                       |   |
|   | description : string      # Beschreibung und Anweisungen      |   |
|   | tags        : string[]    # Kategorien / Schlagwörter         |   |
|   | examples    : string[]    # Beispiel-Prompts                  |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
| authentication (optional)                                             |
|   +---------------------------------------------------------------+   |
|   | schemes : string[]        # z.B. ["Bearer", "Basic"]          |   |
|   | credentials : string      # Hinweis auf Auth-Konfiguration    |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
```

### Task

Die zentrale Arbeitseinheit. Wird vom Client erzeugt, vom Server verarbeitet.

```
Task
+-----------------------------------------------------------------------+
| id         : string              # Eindeutige Task-ID                 |
| sessionId  : string              # Session für zusammengehörende Tasks|
| status     : TaskStatus          # Aktueller Zustand                  |
| history    : Message[]           # Nachrichtenverlauf                 |
| artifacts  : Artifact[]          # Erzeugte Ergebnisse                |
| metadata   : Record<string,any>  # Erweiterte Eigenschaften          |
+-----------------------------------------------------------------------+

TaskStatus
+-----------------------------------------------------------------------+
| state   : TaskState              # Zustand (siehe Zustandsdiagramm)   |
| message : Message (optional)     # Statusnachricht des Agenten        |
+-----------------------------------------------------------------------+
```

### TaskSendParams (Request)

```
TaskSendParams
+-----------------------------------------------------------------------+
| id               : string        # Task-ID                            |
| sessionId        : string        # Session-ID                         |
| message          : Message       # Nachricht mit Parts                |
| historyLength    : number        # Anzahl der History-Einträge        |
| pushNotification : PushConfig    # Push-Benachrichtigungs-Config      |
| metadata         : Record<string,any>                                 |
+-----------------------------------------------------------------------+
```

### Artifact

Das Endergebnis eines Tasks. Grundsätzlich unveränderlich (immutable).

```
Artifact
+-----------------------------------------------------------------------+
| name        : string (optional)  # Bezeichnung des Artifacts          |
| description : string (optional)  # Beschreibung                       |
| parts       : Part[]             # Inhaltsteile                       |
| index       : number             # Position innerhalb des Tasks       |
| metadata    : Record<string,any> # Erweiterte Eigenschaften           |
+-----------------------------------------------------------------------+
| Streaming-Felder:                                                     |
| append      : boolean            # Anhängen an bestehendes Artifact   |
| lastChunk   : boolean            # Letztes Stück im Stream            |
+-----------------------------------------------------------------------+
```

Eigenschaften:
- **Immutable**: Einmal erzeugt, ändert sich der Inhalt nicht
- **Multi-Part**: Ein Artifact kann mehrere Parts enthalten (z.B. Text + Datei)
- **Multi-Artifact**: Ein Task kann mehrere Artifacts erzeugen
- **Streaming**: Parts können schrittweise angehängt werden

### Message

Die Kommunikationseinheit für Prozess- und Steuerungsinhalte (nicht für Ergebnisse).

```
Message
+-----------------------------------------------------------------------+
| role     : "user" | "agent"      # Absender der Nachricht             |
| parts    : Part[]                # Inhaltsteile (ein oder mehrere)    |
| metadata : Record<string,any>    # Optionale Zusatzinformationen      |
+-----------------------------------------------------------------------+
```

#### Abgrenzung Message vs. Artifact

```
+-------------------------+----------------------------+
|        Message          |         Artifact           |
+-------------------------+----------------------------+
| Prozess & Steuerung     | Endergebnis                |
| Veränderlich            | Unveränderlich (immutable) |
| Konversationsfluss      | Ausgabe / Produkt          |
| role: "user" | "agent"  | Kein role-Feld             |
| In history[] des Tasks  | In artifacts[] des Tasks   |
+-------------------------+----------------------------+
```

### Part

Die atomare Inhaltseinheit. Ermöglicht multimodale Kommunikation.

```
TextPart
+-----------------------------------------------------------------------+
| type : "text"                                                         |
| text : string                    # Klartextinhalt                     |
+-----------------------------------------------------------------------+

FilePart
+-----------------------------------------------------------------------+
| type     : string                # MIME-Type (z.B. "image/png")       |
| file                                                                  |
|   +---------------------------------------------------------------+   |
|   | name : string (optional)     # Dateiname                      |   |
|   | uri  : string (optional)     # URL/URI zur Datei              |   |
|   | data : string (optional)     # Base64-kodierter Inhalt        |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+

DataPart
+-----------------------------------------------------------------------+
| type : "application/json"                                             |
| data : object | array            # Strukturierte JSON-Daten          |
+-----------------------------------------------------------------------+
```

### Zusammenspiel der Konzepte

```
+-------------------------------------------------------------------+
|                           Task                                    |
|  +--------------------------------------------------------------+ |
|  |                      history: Message[]                      | |
|  |  +---------------------------+  +-------------------------+  | |
|  |  | Message (role: "user")    |  | Message (role: "agent") |  | |
|  |  |  parts:                   |  |  parts:                 |  | |
|  |  |   +-------------------+   |  |   +-----------------+   |  | |
|  |  |   | TextPart          |   |  |   | TextPart        |   |  | |
|  |  |   | "Suche Reisepass" |   |  |   | "3 gefunden"    |   |  | |
|  |  |   +-------------------+   |  |   +-----------------+   |  | |
|  |  +---------------------------+  +-------------------------+  | |
|  +--------------------------------------------------------------+ |
|  +--------------------------------------------------------------+ |
|  |                    artifacts: Artifact[]                     | |
|  |  +--------------------------------------------------------+  | |
|  |  | Artifact (index: 0)                                    |  | |
|  |  |  parts:                                                |  | |
|  |  |   +-----------------+  +----------------------------+  |  | |
|  |  |   | TextPart        |  | DataPart                   |  |  | |
|  |  |   | "Ergebnisse:"   |  | {documents: [{...}, ...]}  |  |  | |
|  |  |   +-----------------+  +----------------------------+  |  | |
|  |  +--------------------------------------------------------+  | |
|  +--------------------------------------------------------------+ |
+-------------------------------------------------------------------+
```

### Streaming Events

Für lang laufende Aufgaben können Status- und Artifact-Updates gestreamt werden:

```
TaskStatusUpdateEvent
+-----------------------------------------------------------------------+
| id     : string                  # Task-ID                            |
| status : TaskStatus              # Neuer Status                       |
+-----------------------------------------------------------------------+

TaskArtifactUpdateEvent
+-----------------------------------------------------------------------+
| id       : string                # Task-ID                            |
| artifact : Artifact              # Neues/aktualisiertes Artifact      |
+-----------------------------------------------------------------------+
```

---

## JSON-RPC Methoden

Das A2A-Protokoll nutzt JSON-RPC 2.0 als Nachrichtenformat.

| Methode | Richtung | Beschreibung |
|---|---|---|
| `message/send` | Client → Server | Nachricht senden / Task erzeugen |
| `message/stream` | Client → Server | Streaming-Nachricht (SSE) |
| `tasks/get` | Client → Server | Task-Status und Ergebnis abfragen |
| `tasks/cancel` | Client → Server | Task abbrechen |
| `tasks/pushNotification/set` | Client → Server | Push-Notification konfigurieren |
| `tasks/pushNotification/get` | Client → Server | Push-Config abfragen |
| `tasks/resubscribe` | Client → Server | Erneut auf Task-Updates subscriben |

---

## Multi-Agent-Architektur

A2A ermöglicht die Komposition mehrerer Agenten zu einem verteilten System. Ein Agent kann gleichzeitig Server (empfängt Anfragen) und Client (delegiert an andere Agenten) sein.

### Gesamtarchitektur mit mehreren Agenten

```
                          +------------------+
                          |       User       |
                          +--------+---------+
                                   |
                    +--------------v---------------+
                    |     A2A Client Agent         |
                    |  (Orchestrator / Gateway)    |
                    +-----+--+--+------------------+
                          |  |  |
          +---------------+  |  +----------------+
          |                  |                   |
          v                  v                   v
+-------------------+ +-------------------+ +-------------------+
| A2A Server        | | A2A Server        | | A2A Server        |
| Agent 1           | | Agent 2           | | Agent N           |
| (Spring AI)       | | (Python/TS/...)   | | (beliebig)        |
+-------------------+ +-------------------+ +-------------------+
| Skills:           | | Skills:           | | Skills:           |
|  - Skill A        | |  - Skill X        | |  - Skill P        |
|  - Skill B        | |  - Skill Y        | |  - Skill Q        |
+-------------------+ +-------------------+ +-------------------+
|  ChatClient+LLM   | |  LLM/API Backend  | |  LLM/API Backend  |
|  MCP Tools        | |  Eigene Tools     | |  Eigene Tools     |
+-------------------+ +-------------------+ +-------------------+
          |                  |                   |
          v                  v                   v
+-------------------+ +-------------------+ +-------------------+
| Externe APIs      | | Datenbanken       | | Microservices     |
+-------------------+ +-------------------+ +-------------------+
```

### Rollen in der Multi-Agent-Architektur

| Rolle | Beschreibung | Aufgabe |
|---|---|---|
| **Orchestrator** | Zentraler Agent, der Anfragen entgegennimmt und an spezialisierte Agenten verteilt | Routing, Aggregation, Koordination |
| **Spezialist** | Agent mit spezifischen Skills (z.B. Dokumentensuche, Übersetzung, Datenanalyse) | Fachliche Aufgabe ausführen |
| **Gateway** | Einstiegspunkt für externe Clients (UI, API), leitet intern an Agenten weiter | Authentifizierung, Rate Limiting, Protokollübersetzung |

### Remote-Agent-Kommunikation

Der Ablauf, wenn ein Agent Aufgaben an einen anderen delegiert:

```
Dein Agent (Server+Client)              Remote Agent (Server)
         |                                       |
         |  1. AgentCard discovern               |
         |  GET /.well-known/agent-card.json     |
         +-------------------------------------->|
         |                                       |
         |  AgentCard (Skills, URL, ...)         |
         |<--------------------------------------+
         |                                       |
         |  [AgentCard cachen und Skills         |
         |   als lokale Tools registrieren]      |
         |                                       |
         |  2. Message senden                    |
         |  JSON-RPC: message/send               |
         +-------------------------------------->|
         |                                       |
         |  3. Response empfangen                |
         |  Task { status, artifacts }           |
         |<--------------------------------------+
         |                                       |
```

---
