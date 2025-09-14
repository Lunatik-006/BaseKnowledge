``` mermaid
flowchart TD

%% ========= ENTRY & LANGUAGE SELECTION =========
A["/start"] --> B["Hello! Please select your preferred language before starting work. ATTENTION: the choice of language will also affect the processing of the received materials."]

B --> C["/ru"]
B --> D["/en"]

C --> E["all variables in the project responsible for localization are applied in the appropriate run-function depending on the user's choice; all further messages to the user and processing of materials must be in the selected language."]
D --> E
E --> F["Hello message on selected language with usage guide."]

%% ========= TOP-LEVEL MENU =========
F --> G["/menu /help — this button is always available; returns user to previous message with list and explanation of all commands"]
F --> H["/create_project — The button creates a project that will be associated with the added notes and other materials; creates knowledge bases"]
F --> I["/open_project — The button navigates to the project, after which the user can work with its contents"]
F --> S0["/settings — set target_level (beginner/intermediate/advanced), tone (pragmatic/motivational/charismatic), language (ru/en)"]

%% ========= CREATE PROJECT =========
H --> H1["Type your project name"]
H1 --> H2["Project <name> created!"]
H2 --> H3["a message explaining how to work inside the project. Each project can have only one set of data, up to 3 Bases and Courses"]
H3 --> ES0["Empty state: 'Add 5–10 materials to build a draft course structure' (CTA)"]

%% ========= OPEN PROJECT =========
I --> I1["Select which project to open"]
I1 --> I2["mini-menu with buttons '/project1', '/project2', etc"]
I2 --> I3["Project <name> opened!"]
I3 --> ES0

%% ========= BRANCH INTO DATA / MATERIALS =========
H3 --> J["/my_data — User gets access to his uploaded data. View and edit not available in alpha; appears only if user have already uploaded data"]
I3 --> J

H3 --> K["/add_materials"]
I3 --> K

%% ========= ADD MATERIALS =========
K --> K1["Select type of materials"]
K1 --> M1["image"]
K1 --> M2["audio/voice"]
K1 --> M3["text"]
K1 --> M4["video"]

M1 --> N1["Attach or forward image"]
M2 --> N2["Create or forward voice message or attach .mp3/.wav files"]
M3 --> N3["Type or forward message"]
M4 --> N4["Attach or forward file or send link to YouTube"]

N1 --> P["A user can send up to 10 messages in a row with the same type of data."]
N2 --> P
N3 --> P
N4 --> P

P --> Q["Data processed successfully!"]
Q --> R["add more"]
Q --> S["save"]
R --> K
S --> T["all data saved now! You can create Knowledge Base from it!"]

%% ========= MATERIALS LIST / FILTERS / ACTIONS =========
J --> JD1["List of sources with previews (title/first lines/type)"]
JD1 --> JD2["Filters: type (video/text/link), added time"]
JD1 --> JD3["Action: delete from project"]
JD1 --> JD4["Action: open source"]

%% ========= ECONOMY MODE SUGGESTION =========
T --> EM{"Large volume detected?"}
EM -- "YES" --> EM1["Offer 'Economy mode' (faster draft, fewer costs). Explain difference vs full mode"]
EM -- "NO" --> U
EM1 --> U

%% ========= AVAILABILITY CONDITIONS FOR BASE / COURSE =========
U{"Are there any materials in project?"}
V{"Is there knowledge base in project?"}

H3 --> U
I3 --> U
T  --> U

U -- "NO" --> U1["Upload materials firstly"]
U -- "YES" --> V

V -- "NO" --> V1["Create Knowledge Base firstly"]
V -- "YES" --> W["/create_course"]

%% ========= CREATE KNOWLEDGE BASE =========
T --> X["/create_knowledge_base (appears only if user have already uploaded data)"]
X --> X1["The user fills out a small questionnaire to create a Knowledge Base that exactly matches his wishes. He can specify: base name, main topic, main focus, what to focus on, what to avoid, to whom it should be useful, positioning, and his other wishes."]
X1 --> X2["Knowledge Base created successfully"]
X2 --> X3["/save_base"]
X2 --> X4["/edit_base"]
X3 --> X5["/download_base"]
X4 --> X5
X5 --> X6["User gets link to download Knowledge Base"]

%% ========= CREATE COURSE =========
W --> Y00["Prompt: working title of course + 'who is learner' (1 sentence)"]
W --> Y0["User gets the opportunity to give additional suggestions in free form (which will be taken into account when preparing the course). For example, it can be number of lessons, check-list, quiz bank, etc."]
W --> Y1["A vector database is being created based on user's preferences. During use, there is a loader/progress bar. After creation, the user gets access to a preview of the vision draft and the ability to download a zip archive with structured notes; the ability to edit notes."]
Y0 --> Y2["/next_step"]
Y2 --> Y3["old view logic"]
Y3 --> Y4["the structure and content of the course is generated, divided into lessons and sub-topics; the user gets the opportunity to preview and refine the structure and content of the course using prompts manually"]

%% ========= PREVIEW / ACCEPT / REVISE / ROLLBACK =========
Y4 --> Zacc["/accept — fix version v1 of structure"]
Y4 --> Zrev["/revise — reshuffle/rename titles only (keep grouping)"]
Zrev --> Y4
Zacc --> Zv["Version v1 is active"]
Zv --> Zrb["/rollback — return to v1 if v2 was made"]
Zrb -.-> Y4

%% ========= CONTINUE TO GENERATION =========
Y4 --> Z1["/edit_course"]
Y4 --> Z2["/continue"]

Z2 --> Z3["The course is generated strictly in accordance with the previously submitted structure, and includes materials from the knowledge base."]
Z3 --> Zexp["/export — download Obsidian vault + mindmap (markmap)"]
Z3 --> Zkit["/export_kit — download Course Kit (mindmap, outlines, checklists, workbook, quiz bank, 14d content calendar, README)"]
Z3 --> Zopen["Open in Mini App (read-only view of artifacts)"]
Zexp --> Z4["Course generated successfully, now you can download it!"]
Zkit --> Z4
Zopen -.-> Z4

%% Optional loop from edit back to preview/refine
Z1 --> Y4

%% ========= SETTINGS PREVIEW =========
S0 --> S1["Quick preview: how titles/descriptions change with selected style/audience/language (no regrouping)"]
S1 -.-> Y4

%% ========= UX STATES (REFERENCE) =========
subgraph UX_STATES [Reference UX states]
  ST0["Empty — 'Send 5–10 materials to build a draft'"]
  ST1["Loading — building structure / generating kit (progress message)"]
  ST2["Warning — too few/low-quality materials; suggest adding 3–5 more"]
  ST3["Error — unavailable link/invalid content/limit exceeded; explain how to fix"]
  ST4["Success — structure with N modules and M lessons; offer to download kit"]
end

ES0 -.-> ST0
Y1 -.-> ST1
U1 -.-> ST2
X5 -.-> ST4
Z4 -.-> ST4

%% ========= NOTES =========
%% Nothing from the previous version was removed; only extensions and clarifications were added to reflect UX flows (settings, economy mode, preview/accept/revise/rollback, exports, states, list view actions).
```
