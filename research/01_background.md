# Àṣẹ: Background Research

Compiled 17 Nov 2026 for the Mozilla Fellowship 2027 (Track I, host Slum & Rural Health Initiative, Nigeria). Personal project, not Komtora work.

## 1. The host: Slum & Rural Health Initiative (SRHIN)
- Nigerian NGO (Abuja/Ibadan) promoting healthcare access in slums and rural communities across Africa.
- Mental health programmes for young people, e.g. **BraveHeart** (psychoeducation, therapy, life skills), a goal of structured mental health support for 1 million young people, a "Friendship Tent" for displaced people, and a mobile app for youth interventions.
- Runs a **Community Health Intelligence Platform** (MIS) capturing real-time mental and sexual health data, and reportedly has **AI tools trained on anonymised data** from it. So they already collect data and build AI with it; the Fellowship asks how to make that consent-based, community-controlled and benefit-sharing.
- Directory claim: 1.7 million people reached (unverified).
- Their Fellowship ask (RFP): community-owned tools for **governance, consent, privacy and benefit-sharing**, piloted with **young people, people with lived experience, and community health workers**, toward a **mental health data commons**.
- Context: about 80% of Nigerians with serious mental health needs can't access care (Lancet Global Health letter, 2020); mental health gets about 3.3% of the health budget.

## 2. Key ideas and terms (use these words in the application)
| Term | Meaning | Why it matters for Àṣẹ |
|---|---|---|
| **Dynamic consent** | People grant, change or withdraw consent for specific uses over time through a digital tool (Kaye et al., 2015) | Exactly Àṣẹ's core. Known limits: consent fatigue, digital divide, withdrawal not reaching every system |
| **Data commons** | Data treated as a shared resource governed by its community, not owned by one company | SRHIN's stated goal |
| **Data cooperative** | Members pool data and govern it together, e.g. **MIDATA** (Switzerland): one member one vote, users grant access per study, fees from data users reinvested in public-benefit projects, open-source platform | Model for governance and benefit-sharing |
| **CARE principles** (Global Indigenous Data Alliance) | **C**ollective benefit, **A**uthority to control, **R**esponsibility, **E**thics. Complements FAIR open-data principles, which ignore power imbalances | Framework to cite. Àṣẹ maps to each letter |
| **Kaitiakitanga licence** (Te Hiku Media, NZ) | Data holders as *guardians*, not owners; data used only for the community's benefit | Inspiration for a community data-use licence (can't copy its text, it's copyrighted) |
| **ISO/IEC TS 27560:2023** | Standard structure for consent records and consent receipts; reportedly free to download since 2025 | Build Àṣẹ's records to it, so other systems can trust them |
| **Explicit consent** | Nigeria Data Protection Act 2023: health data is *sensitive personal data*; processing generally needs consent that is freely given, specific, informed and clear | Legal basis. Àṣẹ makes consent specific per use and provable |

## 3. The African context
- AU Data Policy Framework (2022) treats data as a sovereign asset, but has no enforcement.
- Kenya's High Court suspended data-sharing parts of a health deal with the US, partly because nothing guaranteed Kenya would benefit from innovations built on its data. Benefit-sharing is a live political issue.
- Proposals in the field: community consultation before deploying AI health tools, local data residency, Ubuntu-based AI ethics (arXiv 2406.10121), community benefit-sharing as a governance pillar.
- Warning worth quoting in spirit: consent protects nobody if it's reduced to a **tap-through**.

## 4. What this means for Àṣẹ's design
1. **Consent per use, not one big "I agree".** Separate yes/no for research, sharing with partners, AI training, etc. (specific consent, NDPA).
2. **Understandable consent.** Plain words, Pidgin and Yoruba, **voice notes** for low-literacy users, short messages. Avoids tap-through consent.
3. **Change or withdraw any time** by WhatsApp message (dynamic consent).
4. **Withdrawal that travels.** When someone withdraws, every approved data user is notified and must confirm deletion or exclusion (fixes the "revocation propagation" weakness).
5. **Collective layer, not only individual.** A community panel (youth reps, people with lived experience, health workers) approves or rejects each data-use request (CARE: authority to control).
6. **Benefit log.** Every approved data use records what comes back to the community (CARE: collective benefit; the Kenya lesson).
7. **Public transparency.** Anyone can see which uses were requested, approved, and what was returned (CARE: responsibility).
8. **Standard records.** Consent records follow ISO/IEC 27560 and are tamper-evident.
9. **No health data inside Àṣẹ.** It stores consent and decisions only. The health data stays in the organisation's own system (e.g. SRHIN's MIS), which checks Àṣẹ before any use.
10. **Avoid consent fatigue.** Ask only when something new is requested, never spam.

## Sources
- [Guardian Nigeria on SRHIN](https://guardian.ng/?p=2646042), [HIFA post](https://hifa.org/node/96849885), [NGO Base profile](https://ngobase.org/profile/314333)
- [CASRAI: dynamic consent](https://casrai.org/dictionary/term/dynamic-consent), [JMIR Med Inform 2026 on withdrawal limits](https://medinform.jmir.org/2026/1/e93348/PDF), [BMC Medical Ethics](https://link.springer.com/content/pdf/10.1186/s12910-023-00988-9.pdf)
- [FPF: Nigeria's Data Protection Act explained](https://fpf.org/blog/nigerias-new-data-protection-act-explained/), [KPMG NDPA review](https://assets.kpmg.com/content/dam/kpmg/ng/pdf/nigeria-data-protection-act2023_kpmg-review.pdf)
- [Oxford: CARE principles](https://researchdata.ox.ac.uk/care-principles), [UK Data Service: CARE](https://ukdataservice.ac.uk/learning-hub/research-data-management/plan-to-share/care-data-principles/)
- [ISO/IEC TS 27560 summary](https://iso27001security.com/html/27560.html), [StandICT entry](https://standict.eu/standards-repository/privacy-technologies-consent-record-information-structure-isoiec-ts-275602023)
- [MIDATA cooperative](https://www.midata.coop/en/cooperative/), [Nesta on MIDATA](https://www.nesta.org.uk/feature/me-my-data-and-i/midatacoop/)
- [Frontiers: data governance in African health research](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11668971/), [Pan African Medical Journal: equitable AI](https://www.panafrican-med-journal.com//content/article/52/179/full), [Tech Policy Press: Nigeria & Kenya](https://techpolicy.press/lessons-from-nigeria-and-kenya-on-digital-colonialism-in-ai-health-messaging), [arXiv Ubuntu framework](https://arxiv.org/pdf/2406.10121)
- [The Spinoff on Te Hiku / Māori data sovereignty](https://thespinoff.co.nz/irl/29-07-2022/indigenous-data-sovereignty-will-make-the-internet-a-better-place-for-maori), [Taiuru on Māori data licences](https://www.taiuru.maori.nz/maori-data-sovereignty-licences/)
