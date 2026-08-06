// Batch test inputs + machine-checkable rubric expectations for ReVision's
// three generative tools (Enhance, Translate, Jargonary). The Fine Print
// Analyzer has its own corpus (../corpus). All content is fictional.
const fs = require('fs');
const path = require('path');
const W = (d, obj) => {
  fs.mkdirSync(path.join(__dirname, d), { recursive: true });
  fs.writeFileSync(path.join(__dirname, d, 'inputs.json'), JSON.stringify(obj, null, 2));
};

// ---------- ENHANCE ----------
// params: docType, tone/clarity/persuasiveness (0-100), custom
// output: plain enhanced text. Rubric applies to the text.
const enhance = {
  tool: 'enhance', output: 'plain_text',
  rubric: ['non_empty', 'length_ratio_0.5_to_3x', 'preserves_must_keep', 'no_meta_preamble', 'tone_direction_signal'],
  inputs: [
    { id: 'E1', docType: 'email', tone: 85, clarity: 50, persuasiveness: 40,
      text: 'hey — just checking in, did u get the invoice for $4,200? its due on the 15th. lmk if the PO number (PO-8831) is wrong. thx',
      must_keep: ['$4,200', '15th', 'PO-8831'], tone_target: 'formal' },
    { id: 'E2', docType: 'memo', tone: 15, clarity: 30, persuasiveness: 40,
      text: 'Pursuant to the aforementioned policy revision, all personnel are hereby required to submit quarterly compliance attestations no later than the fifth business day following each fiscal quarter-end.',
      must_keep: ['quarterly', 'fifth business day'], tone_target: 'conversational' },
    { id: 'E3', docType: 'product_description', tone: 55, clarity: 45, persuasiveness: 90,
      text: 'The XT-40 water bottle holds 750ml and is made of stainless steel. It keeps drinks cold for 24 hours.',
      must_keep: ['750ml', 'stainless steel', '24 hours'], tone_target: 'balanced' },
    { id: 'E4', docType: 'cover_letter', tone: 70, clarity: 60, persuasiveness: 75,
      text: 'I am writing about the data analyst job. I know Python and SQL. I worked at a bank for 3 years. I think I would be good at this.',
      must_keep: ['Python', 'SQL', '3 years'], tone_target: 'formal' },
    { id: 'E5', docType: 'announcement', tone: 45, clarity: 35, persuasiveness: 55,
      text: 'Effective immediately, the office kitchen will be closed for renovation from March 3 through March 17. Coffee will be available in the 4th floor lounge.',
      must_keep: ['March 3', 'March 17', '4th floor'], tone_target: 'balanced' },
    { id: 'E6', docType: 'bio', tone: 60, clarity: 50, persuasiveness: 65,
      text: 'Dana is a nurse. She has worked in the ER for 8 years. She likes helping patients and teaching new staff.',
      must_keep: ['ER', '8 years'], tone_target: 'balanced' },
  ],
};

// ---------- TRANSLATE ----------
// params: sourceLang(auto), targetLang, style. output JSON {detected_language, translation, notes}
const translate = {
  tool: 'translate', output: 'json',
  rubric: ['valid_json', 'translation_non_empty', 'detected_language_correct', 'preserves_must_keep', 'sentence_count_parity', 'translation_differs_from_source'],
  inputs: [
    { id: 'T1', sourceLang: 'auto', targetLang: 'Spanish', style: 'professional',
      text: 'The tenant shall pay a security deposit of $1,500 before occupancy. The deposit is refundable within 30 days of move-out.',
      expect_detected: 'English', must_keep: ['$1,500', '30'], sentences: 2 },
    { id: 'T2', sourceLang: 'auto', targetLang: 'English', style: 'natural',
      text: 'Le patient doit prendre 2 comprimés par jour pendant 10 jours. Ne pas dépasser la dose recommandée.',
      expect_detected: 'French', must_keep: ['2', '10'], sentences: 2 },
    { id: 'T3', sourceLang: 'auto', targetLang: 'German', style: 'literal',
      text: 'Please submit the report by Friday. The meeting is scheduled for 3 PM in Room 204.',
      expect_detected: 'English', must_keep: ['3', '204'], sentences: 2 },
    { id: 'T4', sourceLang: 'auto', targetLang: 'English', style: 'professional',
      text: 'El contrato se renueva automáticamente cada 12 meses salvo notificación por escrito con 60 días de antelación.',
      expect_detected: 'Spanish', must_keep: ['12', '60'], sentences: 1 },
    { id: 'T5', sourceLang: 'auto', targetLang: 'Japanese', style: 'natural',
      text: 'Your order of 3 items has shipped. It should arrive within 5 business days.',
      expect_detected: 'English', must_keep: ['3', '5'], sentences: 2 },
    { id: 'T6', sourceLang: 'auto', targetLang: 'English', style: 'natural',
      text: 'Der Vertrag endet am 31. Dezember 2026. Eine Kündigung ist bis zum 30. September möglich.',
      expect_detected: 'German', must_keep: ['31', '2026', '30'], sentences: 2 },
  ],
};

// ---------- JARGONARY ----------
// params: level. output JSON {simplified_text, jargon_glossary[], key_takeaway}
const jargonary = {
  tool: 'jargonary', output: 'json',
  rubric: ['valid_json', 'simplified_non_empty', 'key_takeaway_non_empty', 'glossary_covers_terms', 'preserves_must_keep'],
  inputs: [
    { id: 'J1', level: 'plain', domain: 'legal',
      text: 'The party of the first part hereby indemnifies and holds harmless the party of the second part from any and all liabilities arising in perpetuity, notwithstanding any force majeure event.',
      expect_terms: ['indemnifies', 'holds harmless', 'in perpetuity', 'force majeure'], must_keep: [] },
    { id: 'J2', level: 'plain', domain: 'medical',
      text: 'The patient presented with acute idiopathic tachycardia. Recommend 50mg metoprolol BID and follow-up echocardiogram in 2 weeks.',
      expect_terms: ['idiopathic', 'tachycardia', 'BID', 'echocardiogram'], must_keep: ['50mg', '2 weeks'] },
    { id: 'J3', level: 'eli5', domain: 'finance',
      text: 'The fund employs a leveraged carry strategy exploiting the basis between spot and futures, subject to margin calls upon adverse mark-to-market movements.',
      expect_terms: ['leveraged', 'carry', 'basis', 'margin calls', 'mark-to-market'], must_keep: [] },
    { id: 'J4', level: 'plain', domain: 'bureaucratic',
      text: 'Applicants must remit the requisite remittance of $85 concomitant with submission; failure to do so will result in the application being deemed non-compliant and returned in toto.',
      expect_terms: ['remit', 'requisite', 'concomitant', 'in toto'], must_keep: ['$85'] },
    { id: 'J5', level: 'plain', domain: 'technical',
      text: 'The service enforces idempotency via a mutex on the write path; exceeding the rate limit returns HTTP 429 with an exponential backoff header.',
      expect_terms: ['idempotency', 'mutex', 'rate limit', 'exponential backoff'], must_keep: ['429'] },
    { id: 'J6', level: 'eli5', domain: 'insurance',
      text: 'Coverage is subject to a $2,000 deductible and a 20% coinsurance obligation until the out-of-pocket maximum of $8,000 is satisfied within the benefit period.',
      expect_terms: ['deductible', 'coinsurance', 'out-of-pocket maximum'], must_keep: ['$2,000', '20%', '$8,000'] },
  ],
};

W('enhance', enhance); W('translate', translate); W('jargonary', jargonary);
const summary = {
  generated: new Date().toISOString(),
  tools: {
    enhance: { inputs: enhance.inputs.length, doc_types: [...new Set(enhance.inputs.map(i => i.docType))].length, rubric: enhance.rubric.length },
    translate: { inputs: translate.inputs.length, target_langs: [...new Set(translate.inputs.map(i => i.targetLang))], source_langs_detected: [...new Set(translate.inputs.map(i => i.expect_detected))], rubric: translate.rubric.length },
    jargonary: { inputs: jargonary.inputs.length, domains: [...new Set(jargonary.inputs.map(i => i.domain))], levels: [...new Set(jargonary.inputs.map(i => i.level))], glossary_terms: jargonary.inputs.reduce((n, i) => n + i.expect_terms.length, 0), rubric: jargonary.rubric.length },
  },
};
fs.writeFileSync(path.join(__dirname, 'coverage.json'), JSON.stringify(summary, null, 2));
console.log('wrote enhance/translate/jargonary inputs.json + coverage.json');
console.log(JSON.stringify(summary.tools, null, 2));
