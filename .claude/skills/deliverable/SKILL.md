---
name: deliverable
description: Turns a reviewer-approved internal report in reports/ into the customer-facing document under deliverables/, written in the customer's language (English by default). Use when a finished report is to be sent to a customer or published as a portfolio sample, or when the user asks for the English / customer version of a report (Turkish: "müşteri sürümü", "İngilizce rapor", "teslim et").
---

# Customer Deliverable

The internal report is the verified record: Turkish, Validator-checked, reviewer-approved. The deliverable
is a **derived document** for the customer: same facts, customer's language, customer's reading order.
You restructure and translate. You never add a finding, never soften one, never change a number.

## Input
- Path of the source report under `reports/`. If not given, ask; do not guess.
- Customer language code (`en`, `tr`, … from `governance/deliverable_languages.json`). Default `en`.
- Customer name, or `portföy örneği` for a portfolio sample.

If the source report's `## Reviewer Kararı` is not `ONAY`, stop and report it. A deliverable may only be
derived from an approved report; the Validator rejects anything else.

## Steps
1. Read the source report in full. Read the language block for your target language in
   `governance/deliverable_languages.json` and the template named there in `governance/templates/deliverable/`.
2. Open the **source file the report names in its `## Kapsam` section** and keep it beside you. Every number
   and every quoted line in the deliverable must come from the report, which you check against this source.
3. Map the content, do not translate line by line:
   - `[OLGU]` → the language's fact label (`FACT` / `OLGU`), with the exact file line or command output.
   - `[ÖNERİ]` → the action label (`FIX` / `ÇÖZÜM`), as a change the customer can apply.
   - `[DOĞRULANMAMIŞ]` → say in plain words what could not be determined and why, marked with the check
     label (`CHECK` / `KONTROL`). Never promote it to a fact; never drop it because it reads badly.
   - `## Doğrulama Durumu` → the `Verification` / `Doğrulama` section, as prose. Do not print the internal
     verdict words (`KABUL`, `BELİRSİZ`); state what was verified and what was not.
4. Write the `Summary` first and make it the headline numbers plus the single most urgent item. The customer
   reads this and nothing else if they are busy.
5. Order findings by severity, highest first. Give each a severity word, not a number.
6. Write the file as `deliverables/YYYY-MM-DD_<skill>_<short-name>_<lang>.md` with the frontmatter filled in
   (`dil`, `kaynak_rapor`, `musteri`, `teslim_tarihi`). The frontmatter is internal traceability; the rendered
   document the customer receives does not show it.
7. Re-read your own file against the source report and count: does every number match, is every finding
   carried over, did any Turkish text survive? Then write your work board note with both paths.

## Limits
- Do not read logs, configs or evidence yourself and do not produce new findings. Your only sources are the
  approved report and the file it cites. You have no Bash and no network on purpose.
- Never write into `reports/`. The internal record is not yours to edit; if you find an error in it, do not
  fix it in the deliverable — write a `HELP REQUEST` line naming the report and the error, and stop.
- No internal label, section heading or verdict word may appear in a non-Turkish deliverable. The Validator
  checks this, but it only matches strings; untranslated prose is your responsibility.
- Do not invent a severity the report does not support, and do not add a recommendation the report does not
  contain — not even an obvious one. Hand it back as a `HELP REQUEST` instead.
- Customer name and host names go in as the user gave them. Do not shorten, correct or anonymise them.
