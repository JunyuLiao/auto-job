# Workflow

`scan` -> deterministic filters -> eligibility -> technical fit -> shortlist -> JD/evidence map -> tailored CV -> independent review -> revision -> PDF/ATS verification -> verified answers -> application bundle -> deterministic form fill -> exact DOM/value read-back -> persisted `REVIEW_READY` screen -> human approval -> manual submission -> outcome tracking.

Priority A receives the full workflow; B receives modest tailoring and verification; C receives standard resume plus eligibility and factual answers. Status values are tracked in Career-Ops and should be updated manually after each real outcome.

The bundle/review boundary is deliberately resumable: a crash can be retried from the immutable bundle, while a changed answer or browser form produces a new hash and requires another review. An unknown question, missing evidence, CAPTCHA, MFA, or ambiguous read-back becomes `MANUAL_REVIEW`.
