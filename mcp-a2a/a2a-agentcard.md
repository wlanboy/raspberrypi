# AgentCard

Die AgentCard ist die "Visitenkarte" eines A2A-Agenten. Sie wird als JSON unter `/.well-known/agent-card.json` bereitgestellt und ermoeglicht anderen Agenten und Clients, die Faehigkeiten des Agenten zu erkennen.

## Interface

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
|   | tags        : string[]    # Kategorien / Schlagwoerter        |   |
|   | examples    : string[]    # Beispiel-Prompts                  |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
| authentication (optional)                                             |
|   +---------------------------------------------------------------+   |
|   | schemes : string[]        # z.B. ["Bearer", "Basic"]          |   |
|   | credentials : string      # Hinweis auf Auth-Konfiguration    |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
| preferredTransport : string      # z.B. "JSONRPC"                     |
| additionalInterfaces : TransportInterface[]                           |
+-----------------------------------------------------------------------+
```

## Discovery-Mechanismus

```
Client                              Server
  |                                    |
  |  GET /.well-known/agent-card.json  |
  +----------------------------------->|
  |                                    |
  |  200 OK                            |
  |  Content-Type: application/json    |
  |  { name, skills, capabilities, ...}|
  |<-----------------------------------+
  |                                    |
  |  [Client cached AgentCard und      |
  |   registriert Skills als Tools]    |
  |                                    |
```

Discovery-Strategien:
- **Well-Known URL**: Standardpfad `/.well-known/agent-card.json`
- **Registry**: Zentrales oder dezentrales Verzeichnis
- **Manuell**: Direkte Konfiguration der AgentCard-URL
