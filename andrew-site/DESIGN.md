---
name: Sentinels
description: A sanitary survey of sewage spills on dry days, one bar per four hours at every site.
colors:
  prussian-blue: "#12355B"
  rain-explained: "#12355B80"
  carmine: "#C8102E"
  survey-yellow: "#E8C547"
  sea: "#BFD6DD"
  land: "#E3E9DF"
  panel: "#F3F6F1"
  ink: "#14202B"
  muted: "#3D5566"
  row-rule: "#C5CEC6"
  white: "#FFFFFF"
typography:
  display:
    fontFamily: "Old Standard TT, serif"
    fontSize: "132px"
    fontWeight: 700
    lineHeight: "120px"
  wordmark:
    fontFamily: "Old Standard TT, serif"
    fontSize: "22px"
    fontWeight: 700
  water-sea:
    fontFamily: "Old Standard TT, serif"
    fontSize: "22px"
    fontWeight: 400
    letterSpacing: "0.08em"
  water-river:
    fontFamily: "Old Standard TT, serif"
    fontSize: "15px"
    fontWeight: 400
  title:
    fontFamily: "Archivo, sans-serif"
    fontSize: "22px"
    fontWeight: 600
  body:
    fontFamily: "Archivo, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "21px"
  body-strong:
    fontFamily: "Archivo, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: "21px"
  link:
    fontFamily: "Archivo, sans-serif"
    fontSize: "15px"
    fontWeight: 500
  label:
    fontFamily: "Archivo, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    letterSpacing: "0.06em"
rounded:
  none: "0px"
spacing:
  bar-gap: "2px"
  stack-gutter: "4px"
  row-y: "9px"
  panel-x: "24px"
components:
  top-bar:
    backgroundColor: "{colors.prussian-blue}"
    textColor: "{colors.sea}"
    height: "56px"
  tab:
    textColor: "{colors.sea}"
    typography: "{typography.body}"
    height: "56px"
  tab-active:
    textColor: "{colors.white}"
    typography: "{typography.body-strong}"
    height: "56px"
  side-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    width: "440px"
    padding: "0 24px"
  table-row:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    padding: "9px 24px"
  table-row-selected:
    backgroundColor: "{colors.survey-yellow}"
    textColor: "{colors.ink}"
    padding: "9px 24px"
  site-label:
    backgroundColor: "{colors.land}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
  site-label-selected:
    backgroundColor: "{colors.survey-yellow}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
  bar-dry-spill:
    backgroundColor: "{colors.carmine}"
    width: "14px"
    height: "4px"
    rounded: "{rounded.none}"
  bar-rain-explained:
    backgroundColor: "{colors.rain-explained}"
    width: "8px"
    height: "4px"
    rounded: "{rounded.none}"
  bar-no-gauge:
    backgroundColor: "{colors.panel}"
    width: "8px"
    height: "4px"
    rounded: "{rounded.none}"
  composer-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
  button-ask:
    backgroundColor: "{colors.prussian-blue}"
    textColor: "{colors.white}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.none}"
  link-more:
    textColor: "{colors.prussian-blue}"
    typography: "{typography.link}"
---

# Design System: Sentinels

Source of record: two static Figma frames at 1440x900, "Sentinels / Overview" and "Sentinels / Open case" (file `lbFyscxUpFForfqBnlQZsB`, nodes 6:2 and 6:452). No code exists yet. Values below are the as-built values of those frames.

## Overview

**Creative North Star: "The Sanitary Survey"**

Sentinels is drawn as a survey sheet, after John Snow's 1854 cholera map and the hand-tinted sanitary surveys of the same period. The map is the document: one flat land tint inside a 1px ink coastline, a pale sea, rivers as thin Prussian-blue lines, and water named in italic serif. Each spill is marked where it happens as a stack of bars, one bar per four hours discharging, so duration is counted rather than read off a scale.

The ground is light because the screen is judged on a projector in a lit room. Colour is rationed by meaning: carmine marks dry-spill candidates and nothing else, survey yellow marks the current selection and nothing else, and Prussian blue carries the shell and the water. Everything a person operates is set in Archivo at one body size; the serif appears only where the sheet speaks as a map: the name, the headline figure and the water.

The system is flat and ruled. Square corners, hairline rules, no shadows, no cards, no gradients, no basemap tiles or texture. It was built in place of a dark basemap with glowing 3D columns and floating stat cards, which is the confirmed anti-reference for this screen. Built so far: two static 1440x900 frames (Overview and Open case). Interaction states, motion, other viewports, a dark theme and the Cases and Reports screens are not designed.

**Key Characteristics:**
- Light, flat survey sheet: sea, land and panel tints with ink linework.
- Bar stacks at each site, one bar per four hours, as the only data mark.
- Carmine for dry-spill candidates only; survey yellow for selection only.
- Old Standard TT for name, figure and water names; Archivo for everything operated.
- Three type sizes: 15px, 22px, 132px.
- Square corners and hairline rules; no shadows, cards or gradients.

## Colors

Flat, hand-tinted map colours on a light ground, with two rationed signal colours.

### Primary
- **Prussian Blue** (#12355B): the shell and the water. Top bar fill, the "Ask" button, agent names in the case thread, the "Show 3 more" link, river lines and water names. At 50% opacity (`rain-explained`) it fills the rain-explained bars, so explained spills recede behind candidates.

### Secondary
- **Carmine** (#C8102E): dry-spill candidates only. The headline figure, the dry bars and their key swatch.

### Tertiary
- **Survey Yellow** (#E8C547): selection only. The 4px rule under the active tab, the selected table row and the selected site label.

### Neutral
- **Survey Sea** (#BFD6DD): the frame ground and the sea. Also the text colour on the Prussian-blue top bar.
- **Land Tint** (#E3E9DF): the single flat fill for land, and the fill of an unselected site label.
- **Sheet** (#F3F6F1): the side panel ground, and the fill of the no-gauge bar.
- **Survey Ink** (#14202B): body text, the coastline, structural rules, and outlines on labels, the field and no-gauge bars.
- **Slate Note** (#3D5566): muted text. Second lines of rows, captions, key notes, model names, the candidate line.
- **Row Rule** (#C5CEC6): the pale hairline between table rows and between messages.
- **Field White** (#FFFFFF): the composer field, and active-tab and button text on Prussian blue.

### Named Rules
**The Carmine Rule.** Carmine marks a dry-spill candidate and nothing else: the headline figure, the dry bars and their key swatch. It is never used for errors, emphasis, links or decoration.

**The Selection Yellow Rule.** Survey yellow means selected, here: the active tab's bottom rule, the selected table row and the selected site label. It is never a highlight, a warning or a fill for anything unselected.

## Typography

**Display Font:** Old Standard TT (with serif fallback)
**Body Font:** Archivo (with sans-serif fallback)

**Character:** A Victorian engraver's serif for what the map says about itself, and a plain modern grotesque for everything a person reads to operate the screen.

### Hierarchy
- **Display** (Old Standard TT Bold 700, 132px, 120px line height): the headline figure, in carmine, over the sea at top left. One per screen.
- **Wordmark** (Old Standard TT Bold 700, 22px): the product name in the top bar.
- **Water names** (Old Standard TT Italic): seas at 22px with 8% tracking, rivers at 15px, both in Prussian blue.
- **Title** (Archivo, 22px): subheads. The figure's caption line and the open case's site name.
- **Body** (Archivo Regular 400, 15px, 21px line height when wrapped): table cells, captions, messages, key labels, tabs, the update time. Muted lines use Slate Note.
- **Body strong** (Archivo SemiBold 600, 15px): site names in rows and labels, agent names, the active tab, the "Ask" button.
- **Link** (Archivo Medium 500, 15px): the "Show 3 more" text link.
- **Label** (Archivo SemiBold 600, 15px, 6% tracking, uppercase): panel section headings ("Longest dry spills", "Case").

### Named Rules
**The Two Voices Rule.** Old Standard TT speaks as the map: the product name, the headline figure and italic water names. Archivo speaks for everything a person reads to operate the screen. Neither crosses over.

**The Three Sizes Rule.** The interface uses 15px, 22px and 132px and no size between them. Hierarchy inside a size comes from weight, muted colour, uppercase tracking and rules.

**The Right-Aligned Figures Rule.** Numbers in columns are right-aligned. Rainfall is printed to two decimals in millimetres, hours to one decimal.

## Layout

A fixed three-part frame at 1440x900, the only viewport built.

- **Top bar**: 56px tall, full width. Product name at left, then the Map / Cases / Reports tabs, with the update time at the right.
- **Map**: fills everything left of the panel (1000px wide at 1440). The land runs off the frame at top and bottom. The headline figure, its caption and the key sit over the sea at the left; the key is separated from the caption by a rule.
- **Side panel**: fixed at 440px on the right, with a 1px ink rule on its left edge. It holds the ranked table "Longest dry spills" (columns Site, Hours, Rain 48 h, mm) above the case thread. In the open case the table shortens to four rows plus "Show 3 more" and the thread takes the remaining height, with the composer at the bottom.
- **Rhythm**: panel content is inset 24px horizontally; table rows carry 9px vertical padding. On the map, bars sit on a 6px pitch (4px bar, 2px gap) and stacks keep a 4px gutter.
- **Density**: one body size throughout, two-line rows, no nested containers.

Not designed: any viewport other than 1440x900, and how the panel or the map behave when the frame is resized.

## Elevation & Depth

None. The system is a single flat sheet with no shadows, blurs or layering. Regions are told apart by flat tint (sea, land, panel) and by 1px rules. A site label sits over the map as an opaque tint with an ink outline, not as a floating layer.

### Named Rules
**The Hairline Rule.** Separation is a 1px rule or a change of flat tint. Nothing casts a shadow, blurs or floats.

## Shapes

Rectangles and drawn lines only. Every box is square-cornered. Structural edges are 1px ink: the panel's left edge, the rule under a section heading, the foot of the table, the rule above the key, and the outlines of labels, the field and no-gauge bars. Lighter divisions between rows and messages use the 1px row rule. The coastline is a 1px ink line (Natural Earth, Great Britain only) and rivers are 1.25px Prussian-blue lines. The one heavier stroke is the 4px yellow rule under the active tab.

### Named Rules
**The Square Corner Rule.** Every corner is square (0px): bars, buttons, fields, labels, rows, the panel.

## Components

Plain, ruled and literal. Only default and selected appearances exist; see "Not designed yet" at the end of this section.

### Bar stack (signature)
Every spill is a stack of bars at its site, one bar per four hours discharging. Bars are 4px tall on a 6px pitch.
- **Dry-spill candidate:** 14px wide, solid carmine.
- **Rain explained:** 8px wide, Prussian blue at 50% opacity.
- **No gauge within 10 km:** 8px wide, panel fill with a 1px ink outline.

**The Countable Bar Rule.** One bar is four hours discharging. Bars are 4px tall on a 6px pitch, so a stack's height is a count, never a continuous scale.

**The Clear Ground Rule.** Stacks keep a 4px gutter from each other and never sit on a river line, the coastline or a label.

**The Candidate Rule.** A carmine stack is a candidate, not proof. The key says "Dry spill candidate" and the open case carries the line "A candidate, not proof. A person approves any report before it is sent."

### Map
One flat land tint with a 1px ink coastline, rivers as 1.25px Prussian-blue lines, sea and river names in italic serif. No basemap tiles, texture or shadow.

### Site label
- **Style:** opaque land tint with a 1px ink outline, square corners. Site name in SemiBold followed by hours in Regular.
- **Selected:** survey-yellow fill, same outline.

### Key
A rule above, then one row per verdict: a three-bar swatch and its label. Muted notes follow ("One bar is four hours discharging.").

### Navigation
- **Top bar:** Prussian-blue fill, 56px tall. Product name in Old Standard TT Bold; update time at right in sea-tint text.
- **Tab:** 15px Archivo Regular in sea tint.
- **Active tab:** white SemiBold text with a 4px survey-yellow rule along the bottom of the bar.

### Table row
- **Style:** two lines. Site name in SemiBold, second line (company and site id) muted. Hours and rainfall right-aligned in their columns. 9px vertical padding, 24px horizontal inset, a row rule beneath.
- **Header:** uppercase section heading with an ink rule beneath, then a column-head row.
- **Selected:** survey-yellow fill across the full panel width.
- **Show more:** "Show 3 more" as a Prussian-blue Medium text link in the place of the hidden rows.

### Message
A hairline rule above, then the agent name in Prussian-blue SemiBold followed by the model in muted Regular, then the body in ink at 15px on a 21px line. Messages are not boxed or bubbled.

### Composer
- **Field:** white fill with a 1px ink outline, square corners, 15px text.
- **Button:** the "Ask" button is attached to the field's right edge, Prussian-blue fill with white SemiBold text.
- The candidate line sits directly above it in muted text.

### Not designed yet
Hover, focus, disabled, loading, error and empty-data states; motion; any viewport other than 1440x900; a dark theme; the Cases and Reports screens. These are open. Design them before building them; nothing in this file specifies them.

## Do's and Don'ts

### Do:
- **Do** mark every discharging site with a bar stack: 4px bars on a 6px pitch, one per four hours.
- **Do** keep dry-spill bars 14px wide in solid carmine and the other two verdicts 8px wide, so candidates read first from the back of the room.
- **Do** separate regions with 1px rules: ink for structural edges, the pale row rule between rows and messages.
- **Do** right-align numbers, with rainfall to two decimals and hours to one.
- **Do** show selection in two places at once: the table row and the site label both turn survey yellow.
- **Do** name the agent and its model on every message, and keep the candidate line above the composer in an open case.

### Don't:
- **Don't** use carmine for anything that is not a dry-spill candidate, or survey yellow for anything that is not the current selection.
- **Don't** add shadows, rounded corners, cards, gradients, basemap tiles or texture.
- **Don't** place a stack on a river line, the coastline or a label, or let stacks touch (4px gutter).
- **Don't** introduce a type size other than 15px, 22px and 132px, or set operated text in Old Standard TT.
- **Don't** present a candidate as a confirmed breach in colour or wording.
- **Don't** treat hover, focus, disabled, loading, error or empty states, motion, other viewports or a dark theme as specified. They are open and need designing before they are built.
