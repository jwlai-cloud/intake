# Second Chair — The Edge, and the Two-Hackathon Plan

Companion to `second-chair-build-spec.md`. That doc's architecture, stack and schedule still stand; amendments are listed in §7.

---

## 1. The honest answer on your edge

I audited two competitor categories I'd previously skipped: mobile field-forms platforms and generic AI notetakers plus real-time sales coaching. The result is uncomfortable and useful.

**Three of the four legs I'd been standing on are already occupied by shipping products.**

| Leg | Status | Who ships it |
|---|---|---|
| Ambient speech → structured form fields | **Dead as novelty** | **Fulcrum Audio FastFill, GA Feb 2025** — handles "cascading options, hidden fields, and conditional logic". Also Appenate AI Voice Fill, Field1st, Inspectly360, Aveni |
| Mandated template with required items + skip logic | **Dead — table stakes** | Every field-forms platform. Do not claim it |
| Live coverage tracking against a template | **Dead as novelty** | **Otter Live Assist (21 Jul 2026)**, Balto AI Checklist, Spiky Active Playbook, Microsoft Teams Facilitator |
| Mid-conversation prompting of what to ask next | **Dead in calls** | Otter, Balto, Spiky, Cresta, Level AI. A 2026 industry analysis argues real-time coaching only became viable this year as latency dropped under 400ms — this is an active land rush, not a vacuum |

**The one I called "crucially" our differentiator is the weakest leg we have.** If you stand in front of a judge and say "nobody prompts you mid-conversation about what you haven't covered," you will be corrected in thirty seconds with a two-week-old press release. Otter's own copy: *"check off objectives live so you always know what's next"*, surfacing *"glanceable tip cards (the question to ask, the point to cover)"*, supporting *"BANT, MEDDIC, and custom frameworks"*, with the stated goal of *"fewer missed qualifiers."*

### What is genuinely unoccupied

Four things, and they're narrower and better than what we had:

**The gate. Nobody withholds the report.** I searched for this directly across every category and found nothing. Inspect Point's fire-safety copilot flags incomplete fields in the field but explicitly declines to gate — "technicians still control the report output and can accept or reject suggestions." Aveni, the most sophisticated adjacent product in the whole audit, gates at *sign-off*, not at generation. **This is your strongest single claim. Make it the headline, not an afterthought.**

**In-person, not on a call.** Balto's own FAQ says it plainly: *"Currently, Real-Time Guidance is only for phone calls."* Otter, Clari, Spiky and Microsoft Facilitator are all video-conference-bound. Fireflies' desktop app does capture in-person conversations — but has no coverage tracking at all. Nobody does live coverage guidance for two humans in a room. **This is a modality moat, not an AI moat, which is exactly why it's durable for a solo builder.**

**Answer-level, not mention-level.** This is the sharpest one. Microsoft Facilitator *"marks topics with a checkmark once the discussion for that topic has started."* Balto ticks when an item is *mentioned*. Otter checks off *objectives*. **Nobody adjudicates whether a required item actually received a real answer.** "Mentioned is not answered" is a five-word competitive claim you can prove on camera.

**Coverage across a branching form.** Fulcrum handles conditional logic on *input*; nobody tracks coverage *across* a skip-logic form where which items are required changes as answers land. That's a real technical claim.

### The reframed claim

> **The only system that treats a mandated form as a live contract during an in-person conversation — tracking answer-level completion of required items across conditional branches while a human professional interviews another human, surfacing the remaining gaps while the subject is still in the room, and withholding the report until every mandatory item has a substantive, evidenced answer.**

Every load-bearing word survives the evidence. **Stop saying:** "ambient AI that fills the form" (Fulcrum, Feb 2025), "AI that tells you what you haven't covered" (Otter, Balto, Spiky, Microsoft), "templates with required fields and skip logic" (everyone).

### The demo beat that wins this argument in fifteen seconds

Have your actor give a vague non-answer. *"Oh, I've had a couple of wobbles."*

A mention-level tracker ticks the falls item — the topic was discussed. **Second Chair does not tick it**, and says the item still needs a specific count and circumstances. Then she asks properly, and it ticks.

That single beat visibly beats Otter, Balto and Microsoft Facilitator simultaneously, and it demonstrates the gate's whole reason to exist. It belongs inside the unedited 75-second take.

### Two threats to price in

**Fulcrum's public roadmap is our product spec, in our words.** Their AI page lists "AI-Guided Hands-Free Fieldwork" — *"context-aware, hands-free experience that can guide work, flag what's missing, prompt next steps"* — status **"Next."** Their vision page promises QA that "spot[s] problems, preventing missed questions." They already ship voice-to-multi-field with conditional-logic handling, and they have the field-forms customer base. **They are one release away.** Not a reason to stop; a reason not to claim the category is empty, and a reason the gate needs to be the headline.

**The architectural substitution attack, which is the sharpest question a judge can ask.** Jotform AI Agents, Maze AI Moderator, HireVue and BrightHire Screen all guarantee completeness by *removing the human interviewer* and letting the AI ask until the form is satisfied. That achieves the completeness goal today. So: **why not just let the AI do the interview?**

The answer has to be about the human, not the technology, and it's a good one. In a regulated field assessment the professional's judgement *is* the deliverable — the form is a record of a qualified human's assessment, not a data-collection exercise, and a form filled by a machine isn't the same artifact legally or professionally. The interviewer is simultaneously observing the environment, checking things physically, judging whether an answer is evasive, and holding accountability for what gets signed. And the subject is often frightened, confused or vulnerable, and consent to be interviewed by a machine is not a given.

Which is precisely why the product is called **Second Chair**. The name is the answer to the hardest objection, which is a good sign it's the right name.

---

## 2. Two versions — and they map cleanly onto two hackathons

Your instinct is right, and better than you probably realised, because the two builds serve two different contests:

| | Web (laptop + mic) | iOS |
|---|---|---|
| Purpose | **All Things Agentic submission** | **Shipaton submission** |
| Why | The rules say a hosted URL is *"highly encouraged"* — judges can click and try it. Removes the entire app-store question from the ATA entry | Shipaton **requires** a store-published native app; web is explicitly ineligible |
| Effort | Flutter builds to web from the same codebase | Same codebase, iOS target |

**One caveat I have not verified:** Flutter web audio capture. The `record` package claims web support via MediaRecorder, but browser mic capture in Flutter web has historically been the rough edge, and bundle size and performance can bite. **Spend thirty minutes on a throwaway spike before Weekend 2 commits you.** If it fights you, the fallback is a plain HTML/JS front end talking to the same Cloud Run backend — the backend is where all the intelligence lives, so a second thin client is cheap.

---

## 3. Shipaton — verified, and it changes the App Store advice

**RevenueCat Shipaton 2026 is running.** Submission period **31 Jul – 30 Sep 2026, 11:45pm PDT** · judging 1–13 Oct · winners 21 Oct · Grand Prize **$100,000**, total cash pool around $685k across many categories.

Three requirements that matter:

**App store publication is mandatory.** *"Software applications must be built for iOS, iPadOS, macOS, or Android and must be fully published to Apple's App Store, the Google Play Store, or the Samsung Galaxy Store by the submission deadline."* So **my "don't ship to the App Store" advice reverses for Shipaton** — it's the entry requirement. It stands for ATA, where nothing asks for it and the freeze clause makes it a liability.

**RevenueCat SDK powering a purchase is mandatory.** *"Entrants must create a working software application that uses the RevenueCat SDK to power at least one in-app or web purchase, or that serves ads through RevenueCat Ads."* You need a real paywall. An honest one for this product: free tier gets one template and a few sessions a month; paid unlocks custom templates, unlimited sessions and Drive export.

**Web is ineligible.** *"A submitted Project must run on iOS, iPadOS, macOS, or Android."* Hence the split in §2.

### The two "newly created" clauses are asymmetric, and that asymmetry is the whole opportunity

- **ATA gates on when the code was written:** *"Projects must be newly created during the Submission Period"* (3–31 Aug), with pre-existing code allowed but **required to be disclosed**.
- **Shipaton gates on first public store release:** *"A Project may have existed before the Submission Period, but it must not have been publicly released on any eligible store before the Submission Period."* Pre-existing code is explicitly fine.

Code written in August satisfies both. **No contradiction.**

### Is dual submission allowed?

**Grey, leaning clearly allowed.** I searched both full rule sets for "other contest", "other hackathon", "concurrent", "previously submitted", "elsewhere". **Neither contains any restriction on entering the same project in another competition.** Both IP grants are **non-exclusive**, so no conflict there. Shipaton has no FAQ page at all, so there's no supplementary guidance either way — this is an absence-of-prohibition finding, not affirmative permission, and both sponsors retain broad sole-discretion disqualification rights.

Two structural points in your favour. ATA's freeze applies to the **Submission**, not the codebase — the rules say explicitly that after the deadline *"you may not make any changes or alterations to your Submission, **but you may continue to update the Project**."* And a Devpost page, public repo, demo video or web deployment are **not** eligible-store releases, so an August ATA entry doesn't burn Shipaton eligibility.

### Safest structuring

One repo, not two — separate repos would create a false paper trail and make both contests' sole-ownership warranties harder to evidence. Tag `ata-submission-2026-08-31` at the ATA deadline and point the ATA entry at the **tag**, not `main`, so the frozen submission is provable while you keep building. Then September is Shipaton work: RevenueCat paywall, App Store polish, store review, growth.

**One correction:** the ATA window opens **3 August at 9:00am PT**, not the 4th. You're clear either way, but if any of this codebase predates the 3rd, disclose it in the write-up. Undisclosed pre-window work is the single highest-probability disqualification path in either contest.

**If you want certainty, ask in writing.** `cloudhackathons@google.com` is the ATA contact in the rules; RevenueCat has an official Shipaton Discord. Given both sponsors' unfettered discretion, a written reply is worth more than any inference from silence, and asking costs nothing.

### The App Store problem you now have to solve

Since Shipaton requires publication, the guidelines I flagged last round now bite. **Guideline 5.1.1(ix)** says apps in regulated fields *including healthcare* *"should be submitted by a legal entity that provides the services, and not by an individual developer."* If your Apple account is Individual, a healthcare-positioned listing is a probable rejection, and switching enrollment needs D-U-N-S verification you can't get in time.

**The fix is easy and honest:** position the App Store listing generically — a structured-interview and report companion for field professionals — and let the loss-adjusting and inspection templates be the marketing surface. Healthcare becomes one config the user can load, not the product's identity. That's true by architecture, so it isn't a dodge. Keep clinical claims, accuracy claims and diagnostic language out of the metadata entirely.

Also note Shipaton needs a genuinely **finished** app, not a demo build — guideline 2.2 explicitly bars demos and betas from the store. That's a higher bar than ATA, which is another reason to sequence: ATA in August, hardening in September.

---

## 4. Export — email, Drive, and the cheap trick

Report export is a good "takes real action" beat, and Google Drive in a Google hackathon is thematically right.

For v1, the share sheet and `mailto:` cost nothing. For Drive, skip user OAuth — the consent-screen dance on mobile is exactly the kind of fiddly work that eats an evening for no demo value. **Use a service account writing to a designated folder instead.** On camera it's indistinguishable from user OAuth, and it's a fraction of the work. Swap to real OAuth later if the product goes anywhere.

Future integrations worth naming in "What's next" rather than building: direct writeback to the system of record (the actual pain — she still retypes into the EHR or claims system), offline capture with deferred sync (**no vendor I audited documents offline operation, and it's the most underserved requirement in the whole market**), and multi-speaker separation when a family member or carer is also in the room.

---

## 5. Revised positioning for the submission

The two-axis framing is the clearest way to make the edge legible to a judge in one slide:

**Field-forms platforms** — Fulcrum, SafetyCulture, Appenate, TrueContext — have the mandated form, the skip logic, the report export, and now voice-to-field. But they assume a lone inspector *narrating to the app*. They don't know a conversation is happening. No second party, no coverage prompting.

**Live coaching and notetakers** — Otter Live Assist, Balto, Spiky, Microsoft Facilitator — know a conversation is happening, track coverage, prompt live. But their "template" is a soft agenda: no typed fields, no validation, no branching, no gate. And they are all bound to calls.

**Second Chair is the intersection.** One category brought the form; the other brought the conversation. Nobody has put a *gate* on either, and nobody has taken it into a room.

---

## 6. Amendments to the build spec

- **§5 of the spec (App Store: no)** — still correct **for ATA**. Reverses for Shipaton, which requires publication. See §3 above.
- **§9 demo** — add the vague-non-answer beat from §1 into the unedited 75-second take. It's now the most valuable fifteen seconds in the video.
- **§11 differentiation claim** — replace with the reframed claim in §1. The old one leaned on mid-conversation prompting, which Otter now ships.
- **§8 schedule** — add a 30-minute Flutter web audio spike before Weekend 2. Add "web build" to Weekend 2, "Drive export via service account" to the 17–21 Aug evenings.
- Everything else — architecture, config schema, stack, memory design, guardrails — unchanged.

---

## 7. Open items, revised

**Verify yourself, high value:** **BrightHire's live interview guide.** Their product page promises *"a real-time guide… prompting your interviewers with the right questions."* I could not determine from marketing pages whether it *dynamically detects* which questions have been asked and answered, or merely displays a static list live. My read is static-list-shown-live — their 2025 product recap is silent on coverage detection, which is telling — but this is the one competitor that could hold a genuine prior claim. **Book a demo before you stand behind the answer-level claim on camera.**

**Also unverified, lower stakes:** Gong's real-time tier (third-party mention only); Cresta, Hyperbound and Level AI's "missed discovery question" prompts (asserted by a 2026 industry analysis, not vendor-confirmed — but Balto and Spiky *are* confirmed, so assume real); Attention's current real-time status (site reads post-call only now); Device Magic entirely (no primary source reachable); whether any product gates output undocumented in a regulated vertical. Clinical trials, HR investigations and journalism were searched shallowly — treat as "no evidence found", not "empty".

**Your own to-dos:** whether your Apple Developer account is Individual or Organization; whether her template and guidance notes contain anything confidential to her employer; whether Flutter web audio capture works acceptably.

---

## 8. Sources

Hackathons: [All Things Agentic rules](https://allthingsagentichackathon.devpost.com/rules) · [ATA FAQs](https://allthingsagentichackathon.devpost.com/details/faqs) · [Shipaton 2026 rules](https://revenuecat-shipaton-2026.devpost.com/rules) · [Shipaton 2026](https://revenuecat-shipaton-2026.devpost.com/) · [RevenueCat announcement](https://www.revenuecat.com/blog/company/announcing-shipaton-2026)

Field-forms platforms: [Fulcrum Audio FastFill PR, Feb 2025](https://www.prnewswire.com/news-releases/fulcrum-audio-fastfill-a-first-of-its-kind-ai-innovation-302374796.html) · [Fulcrum AI roadmap](https://www.fulcrumapp.com/ai-field-data-collection/) · [Fulcrum vision](https://www.fulcrumapp.com/vision/) · [SafetyCulture AI tools](https://safetyculture.com/ai-tools) · [SafetyCulture AI Assistant](https://help.safetyculture.com/005770) · [TrueContext 2026 roadmap](https://truecontext.com/blog/truecontext-2026-product-roadmap-ai-augmented-future/) · [Appenate AI features](https://www.appenate.com/new-ai-features/) · [Appenate acquires Forms On Fire](https://www.appenate.com/blog/appenate-acquires-forms-on-fire/) · [GoCanvas AI Forms](https://www.gocanvas.com/products/tour-ai-forms) · [Jotform AI Agents](https://www.jotform.com/ai/agents/) · [Field1st voice forms](https://field1st.com/features/voice-safety-forms/) · [Inspect Point Inspection Assistant](https://www.einpresswire.com/article/854038144/inspect-point-launches-the-industry-s-first-ai-powered-co-pilot-specific-to-fire-life-safety-inspection-assistant)

Live coaching and notetakers: [Otter Live Assist, 21 Jul 2026](https://www.businesswire.com/news/home/20260721446216/en/Otter.ai-Introduces-Live-Assist-The-First-Live-Coaching-Agent-for-Every-Call) · [Otter AI sales workflow](https://otter.ai/blog/how-to-build-ai-sales-workflow-otter) · [Balto Real-Time Agent Assist](https://www.balto.ai/real-time-agent-assist/) · [Balto FAQ](https://www.balto.ai/faq/) · [Microsoft Facilitator in Teams](https://support.microsoft.com/en-us/teams/copilot/facilitator-in-microsoft-teams-meetings) · [Granola templates](https://docs.granola.ai/help-center/taking-notes/customise-notes-with-templates) · [Fireflies Live Assist](https://markets.financialcontent.com/newsok/article/gnwcq-2025-11-13-fireflies-launches-live-assist-and-desktop-app-to-deliver-real-time-help-in-every-meeting) · [Clari Copilot](https://www.clari.com/products/copilot/) · [Spiky](https://spiky.ai/) · [BrightHire product](https://brighthire.com/product/) · [Metaview](https://www.metaview.ai/interview-notes) · [Aveni clarification prompts](https://aveni.ai/blog/how-ai-clarification-prompts-prevent-incomplete-suitability-documentation/) · [Maze AI Moderator](https://maze.co/features/ai-moderator/)

Apple: [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
