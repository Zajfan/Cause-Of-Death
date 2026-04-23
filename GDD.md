# Cause of Death — Game Design Document

## High concept

A detective game about solving murders through observation, deduction, and evidence handling. The player does not fight enemies in action scenes; instead they fight uncertainty, lies, and bad assumptions.

## Fantasy

You are the investigator who can solve impossible murders by reconstructing what really happened.

## Tone

- Serious
- Tense
- Grounded
- Mystery-driven
- Procedural but dramatic

## Player experience

The player should feel like they are:

- Searching a crime scene carefully
- Comparing statements against evidence
- Spotting contradictions
- Building a theory from fragments
- Making a final decision under pressure

## Core pillars

### 1. Evidence first
Every important conclusion should come from something the player can inspect.

### 2. Logical deduction
The correct answer should follow from the facts, not from trial and error.

### 3. Rich case materials
Cases should include text, photos, audio, video, receipts, messages, and forensic results.

### 4. UI-driven investigation
The entire game should be playable through a strong desktop interface.

### 5. Replayable mystery content
Different cases can vary by culprit, motive, method, and evidence structure.

## Core loop

1. Open a case file
2. Study the victim, suspects, and known facts
3. Inspect evidence objects
4. Mark contradictions and useful leads
5. Build a hypothesis
6. Test the hypothesis against the evidence
7. Accuse a suspect
8. Get resolution, scoring, and unlocks

## Main systems

### Case file system
Each case contains:

- Victim profile
- Suspect list
- Scene summary
- Timeline
- Evidence inventory
- Hidden truth
- Optional side clues

### Evidence system
Evidence types should include:

- Text notes
- Photos
- Audio clips
- Video clips
- Documents
- Maps and floor plans
- Forensic reports
- Phone logs or message transcripts
- Objects found at the scene

### Scene examination
Crime scenes should allow the player to inspect areas and discover:

- Blood patterns
- Missing items
- Damage or forced entry
- Time-of-death indicators
- Hidden objects
- Contradictory details

### Suspect system
Suspects need:

- Motivation
- Opportunity
- Behavior profile
- Alibi
- Relationship to victim
- Lie detection through contradiction

### Deduction board
A central UI surface where the player can:

- Pin evidence
- Connect clues
- Build timelines
- Mark suspects as likely or unlikely
- Draft theory versions

### Final accusation
The player submits:

- Killer identity
- Method
- Motive
- Key evidence

## Puzzle design

Puzzles should not feel random. They should be built around investigation logic, such as:

- Matching timestamps
- Comparing visual details across photos
- Listening for details in audio
- Spotting altered documents
- Reconstructing room layout from clues
- Identifying false alibis

## Case structure

A good case can follow this pattern:

- Opening incident
- Scene investigation
- First suspect round
- Evidence expansion
- Twist reveal
- Final reasoning
- Accusation

## UI ideas

- Left panel: case navigation
- Center panel: evidence viewer
- Right panel: notes, suspects, or timeline
- Bottom panel: actions and filters

## Scoring

Score can reflect:

- Accuracy of accusation
- Time taken
- Number of optional clues found
- Correct reconstruction of motive and method
- Whether the player used hints

## Content types

The game should support more than simple murder cases:

- Locked-room murders
- Poison cases
- Staged suicides
- Missing-person cases that become murders
- Serial killer investigations
- Conspiracy-linked homicides
- Domestic crime scenes

## Suggested technical direction

For a desktop build, a good starting path would be:

- UI app with Electron or Tauri
- Local case data stored as files
- Media viewer for images/audio/video
- Narrative and clue data in structured JSON or markdown
- Rules engine for validating accusations

## Expansion ideas

- Case editor for creating new mysteries
- Randomized case generator
- Hint system
- Detective rank progression
- Evidence difficulty modes
- Branching endings
- Community-made cases
