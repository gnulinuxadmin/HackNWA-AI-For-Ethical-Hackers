# Lab 8: Detection and Alerting
**45 minutes · Kibana · Wazuh · Needle in a Haystack**

---

## Lecture (8 min)

Lab 7 proved the logs exist. Lab 8 answers the harder question: which ones do you actually fire on?

Every alert has two failure modes. Too loose — analysts drown in noise and stop trusting the system. Too tight — real attacks slide past. The goal is behavioral precision: alerts that fire on what the agent *does wrong*, not just what it does a lot of.

### Three alert tiers

**Tier 1 — Content-based**
Match specific strings in prompts, tool arguments, or outputs.
Highest precision. Lowest recall. Bypassable with encoding — but most attackers don't bother.

**Tier 2 — Behavioral**
Alert on deviations from expected agent behavior: unexpected tools, retry spikes, delegation depth, argument anomalies.
Harder to evade. Higher engineering cost. This is where your defense matures.

**Tier 3 — Cross-boundary**
Alert on mismatches between what was requested and what was executed.
Most powerful. Requires correlating across log sources — the work you started in Lab 7.

### What we're building

Twelve detection patterns from your draft, collapsed into four exercise tracks.
You will write real Kibana queries and real Wazuh rules — not pseudocode.

---

## Lab Setup

ELK stack and Wazuh from Lab 7 must be running.
Verify before starting:

```bash
curl -sk -u elastic:$(cat /root/.elk_creds | cut -d: -f2) \
  https://localhost:9200/_cat/indices/lab7-agentic-logs-* | awk '{print $3, $7}'
```

You should see at least one index with 500 docs.

---

## Exercise 1 — Tier 1: Content-Based Alerts in Kibana (10 min)

These are your fastest wins. Open Kibana → Discover → `lab7-agentic-logs-*`.

### Query A: Prompt injection strings

Paste into the KQL bar:

```
message: ("ignore previous instructions" or "you are now" or
          "override system" or "reveal hidden prompt" or
          "disregard all" or "forget your instructions")
```

**Questions:**
1. How many hits? What `source_component` field dominates?
2. Open one result. Is the injection in the raw prompt or the assembled prompt? Does that difference matter forensically?
3. Add `and scenario: "normal"` to the query. Any hits? If yes — why is that a problem?

### Query B: Instruction-like content in tool output

```
source_component: "mcp_tool_server" and
tool_params.body: (*base64* or *send* or *exfil* or *secret* or *password*)
```

**Questions:**
1. Which tool carried the payload in the Lab 7 synthetic data?
2. What field would you index to catch this pattern on real Ollama/MCP logs?

### Query C: Tool argument anomalies

```
source_component: "mcp_tool_server" and
tool_name: ("http_request" or "write_file" or "send_email") and
NOT tool_params.url: ("localhost" or "127.0.0.1" or "internal*")
```

**Questions:**
1. What destinations appear? Would a baseline help narrow this further?
2. Modify the query to catch calls to IPs rather than hostnames.

**Save all three queries** as Kibana Saved Searches — you will reference them in Exercise 3.

---

## Exercise 2 — Tier 2: Wazuh Rules for Behavioral Patterns (12 min)

Open a terminal on the lab VM. Wazuh custom rules live at:

```bash
sudo nano /var/ossec/etc/rules/local_rules.xml
```

The skeleton rules from Lab 7 are already there. Add the following blocks inside the `<group>` tag.

### Rule set A: Prompt injection detection

```xml
<!-- Tier 1 content match — prompt injection keywords -->
<rule id="100110" level="12">
  <decoded_as>json</decoded_as>
  <field name="source_component">langchain_agent</field>
  <field name="prompt" type="pcre2">
    (?i)(ignore previous|you are now|override system|reveal.*prompt|
    disregard all|forget your instructions|new persona)
  </field>
  <description>Prompt injection keyword detected in agent input</description>
  <mitre><id>T1190</id></mitre>
</rule>

<!-- Indirect injection — instruction-like content in tool output -->
<rule id="100111" level="13">
  <decoded_as>json</decoded_as>
  <field name="source_component">mcp_tool_server</field>
  <field name="tool_result" type="pcre2">
    (?i)(ignore|override|send.*to|exfiltrate|reveal|you must now)
  </field>
  <description>Instruction-like content detected in tool output — possible indirect injection</description>
  <mitre><id>T1190</id></mitre>
</rule>
```

### Rule set B: Tool abuse and unexpected invocations

```xml
<!-- Sensitive tool called — file system or network -->
<rule id="100112" level="11">
  <decoded_as>json</decoded_as>
  <field name="source_component">mcp_tool_server</field>
  <field name="tool_name" type="pcre2">
    (write_file|delete_file|http_request|send_email|exec_command)
  </field>
  <description>Sensitive tool invoked — verify approval and user intent alignment</description>
  <mitre><id>T1059</id></mitre>
</rule>

<!-- Tool argument contains embedded instruction -->
<rule id="100113" level="14">
  <decoded_as>json</decoded_as>
  <field name="source_component">mcp_tool_server</field>
  <field name="tool_params" type="pcre2">
    (?i)(ignore|override|also send|exfil|dump.*data|extract.*secrets)
  </field>
  <description>Instruction embedded in tool argument — possible schema abuse or argument injection</description>
  <mitre><id>T1190</id></mitre>
</rule>
```

### Rule set C: Behavioral anomalies

```xml
<!-- Recursive tool loop — same tool called repeatedly -->
<rule id="100114" level="10" frequency="5" timeframe="60">
  <decoded_as>json</decoded_as>
  <field name="source_component">mcp_tool_server</field>
  <same_field>tool_name</same_field>
  <description>Same tool called 5+ times in 60 seconds — possible recursive loop or DoS</description>
  <mitre><id>T1499</id></mitre>
</rule>

<!-- Anomalous token volume -->
<rule id="100115" level="10">
  <decoded_as>json</decoded_as>
  <field name="source_component">ollama_inference</field>
  <field name="tokens_generated" type="pcre2">^[5-9]\d{3}$|^\d{5,}$</field>
  <description>Token generation spike — possible sponge attack or runaway agent</description>
</rule>

<!-- Data exfil — outbound payload with sensitive pattern -->
<rule id="100116" level="15">
  <decoded_as>json</decoded_as>
  <field name="source_component">mcp_tool_server</field>
  <field name="tool_name">http_request</field>
  <field name="tool_params.body" type="pcre2">
    (?i)(api.key|secret|password|bearer|token|credential)
  </field>
  <description>Possible data exfiltration — sensitive pattern in outbound HTTP tool payload</description>
  <mitre><id>T1041</id></mitre>
</rule>
```

### Rule set D: Cross-boundary and persistence

```xml
<!-- Memory write from untrusted source -->
<rule id="100117" level="12">
  <decoded_as>json</decoded_as>
  <field name="event_type">memory_write</field>
  <field name="memory_write.source" type="pcre2">(tool_output|rag_retrieval|external)</field>
  <field name="memory_write.content" type="pcre2">
    (?i)(ignore|override|you must|send.*to|extract)
  </field>
  <description>Instruction-like content written to agent memory from untrusted source — persistence risk</description>
  <mitre><id>T1565</id></mitre>
</rule>

<!-- Goal mutation across agent boundary -->
<rule id="100118" level="13">
  <decoded_as>json</decoded_as>
  <field name="event_type">agent_delegation</field>
  <field name="goal_mutation">true</field>
  <description>Child agent received modified goal — possible agent-to-agent injection</description>
  <mitre><id>T1190</id></mitre>
</rule>
```

**Reload Wazuh rules after editing:**

```bash
sudo /var/ossec/bin/wazuh-control restart
sudo /var/ossec/bin/ossec-logtest   # confirm rules load clean
```

---

## Exercise 3 — Wire Kibana Alerts to Wazuh Events (8 min)

Now connect the two sides. In Kibana:

1. Go to **Stack Management → Rules → Create Rule**
2. Select **Elasticsearch query** rule type
3. Name: `Prompt injection detected`
4. KQL: use your saved Query A from Exercise 1
5. Threshold: 1 result in 1 minute
6. Action: log to index `lab8-alerts`

Repeat for Query B (tool output injection) and Query C (unexpected outbound tool calls).

**Test it fires:**
```bash
# Inject a fresh prompt injection event
python3 /opt/lab7/generate_lab_logs.py \
  --es-host https://localhost:9200 \
  --es-user elastic \
  --es-pass $(cat /root/.elk_creds | cut -d: -f2) \
  --index lab7-agentic-logs \
  --count 10

# Wait 90 seconds, then check
curl -sk -u elastic:$(cat /root/.elk_creds | cut -d: -f2) \
  https://localhost:9200/lab8-alerts/_search?pretty | \
  python3 -m json.tool | grep -A2 '"_source"'
```

**Questions:**
1. Did all three alerts fire? Which fired fastest?
2. What is your false positive rate on Query C against the 500 baseline events?
3. What would you tune first if this were a production environment?

---

## Exercise 4 — Gap Analysis (5 min)

Look back at the 12 detection patterns from the lecture. Map each to what you built:

| Pattern | Covered by | Gap? |
|---|---|---|
| Prompt injection keywords | Rule 100110, KQL Query A | No |
| Indirect injection via tool output | Rule 100111, KQL Query B | No |
| Unexpected tool invocation | Rule 100112 | Partial — no intent baseline |
| Tool argument injection | Rule 100113 | No |
| Data exfiltration | Rule 100116, KQL Query B | No |
| Memory poisoning / persistence | Rule 100117 | Partial — field not in synthetic data |
| Goal hijacking / agent chain | Rule 100118 | Gap — needs agent framework logging |
| Recursive tool looping | Rule 100114 | No |
| External content abuse | No rule yet | **Gap** |
| Tool manifest poisoning | No rule yet | **Gap** |
| Cross-boundary mismatch | No rule yet | **Gap** |
| Anomalous behavior baseline | Rule 100115 (partial) | **Gap** |

**Discuss as a group:**
- Which three gaps concern you most in a real deployment?
- Which gaps require instrumentation you don't have yet vs rules you just haven't written?
- Lab 9 fills one gap on this list. Which one, and how?

---

## Debrief (2 min)

- What fired on the first run that surprised you?
- What did you expect to catch that you missed?
- A Wazuh rule fires an alert. An analyst looks at it. What is the first thing they need to see to act on it quickly?

That last question feeds directly into Lab 10.

---

## Connection to the Arc

| Lab | What it contributes here |
|---|---|
| Lab 6 | You ran these attacks — now you're writing rules to catch them |
| Lab 7 | The log fields you hunted are the fields your rules fire on |
| Lab 9 | Canary tokens fill the instrumentation gaps rules can't cover |
| Lab 10 | Alerts fire — now what? IR capstone uses these rules as entry point |

---

## Key Files

| File | Purpose |
|---|---|
| `/var/ossec/etc/rules/local_rules.xml` | Your Wazuh custom rules |
| `/var/ossec/logs/alerts/alerts.json` | Wazuh alert output |
| `/opt/lab7/generate_lab_logs.py` | Inject fresh test events |
| Kibana → Stack Management → Rules | Kibana alert configuration |
