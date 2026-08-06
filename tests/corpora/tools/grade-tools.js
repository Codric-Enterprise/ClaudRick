#!/usr/bin/env node
// Live grader for Enhance / Translate / Jargonary. Replicates each tool's exact
// prompt from src/revision/static/index.html, POSTs to a running ReVision server
// (non-streaming), and applies the machine-checkable rubric in each inputs.json.
//   ANTHROPIC_API_KEY=sk-ant-... revision &
//   node grade-tools.js http://localhost:8000 [enhance|translate|jargonary|all]
const fs = require('fs');
const path = require('path');
const BASE = process.argv[2] || 'http://localhost:8000';
const ONLY = process.argv[3] || 'all';

const styleInstructions = {
  professional: 'This is a professional/legal document. Preserve precise meaning, legal terminology equivalents, and formal register. Accuracy of meaning takes priority over natural flow.',
  natural: 'Translate naturally, the way a fluent native speaker would express these ideas. Prioritize readability and natural phrasing.',
  literal: 'Translate as literally as possible while remaining grammatical. Stay close to the original word choices and sentence structure.',
};
const levelInstructions = {
  plain: 'Rewrite in plain English for a general adult reader. Use everyday words, short sentences, and active voice. Aim for roughly an 8th grade reading level.',
  simple: 'Rewrite very simply, as if explaining to someone completely new to this field. Define anything even slightly technical. Aim for roughly a 5th grade reading level.',
  eli5: 'Rewrite as if explaining to a smart five-year-old. Use simple analogies from everyday life. No technical words at all.',
};

const buildPrompt = {
  enhance: (i) => `You are a professional document enhancement specialist. Enhance this ${i.docType.replace(/_/g, ' ')} document based on these specifications:

TONE (0=Conversational, 100=Formal): ${i.tone}
- Target: ${i.tone < 40 ? 'conversational' : i.tone > 60 ? 'formal & authoritative' : 'balanced'}
CLARITY (0=Simple, 100=Detailed): ${i.clarity}
- Target: ${i.clarity < 40 ? 'simple & direct' : i.clarity > 60 ? 'detailed & nuanced' : 'balanced'}
PERSUASIVENESS (0=Neutral, 100=Compelling): ${i.persuasiveness}
- Target: ${i.persuasiveness < 40 ? 'neutral & objective' : i.persuasiveness > 60 ? 'compelling & engaging' : 'balanced'}

${i.custom ? `ADDITIONAL INSTRUCTION: ${i.custom}` : ''}

ORIGINAL DOCUMENT:
${i.text}

Provide ONLY the enhanced document text, no explanations or meta-commentary. Maintain the original structure and intent while applying the requested enhancements.`,
  translate: (i) => `You are a professional translator. ${i.sourceLang === 'auto' ? 'First detect the source language, then translate' : `Translate from ${i.sourceLang}`} to ${i.targetLang}.

STYLE: ${styleInstructions[i.style]}

Return ONLY valid JSON (no markdown fences):
{
  "detected_language": "the source language name",
  "translation": "the full translated text, preserving paragraph breaks",
  "notes": "optional: 1-2 brief notes on any terms that don't translate directly or where meaning could shift (empty string if none)"
}

TEXT TO TRANSLATE:
${i.text}`,
  jargonary: (i) => `You are Jargonary, a jargon-decoding assistant. Analyze this dense text and simplify it.

SIMPLIFICATION LEVEL: ${levelInstructions[i.level]}

Return ONLY valid JSON (no markdown fences):
{
  "simplified_text": "the full rewritten text at the requested level, preserving all substantive meaning and any obligations, deadlines, or numbers",
  "jargon_glossary": [ { "term": "...", "plain_meaning": "...", "why_it_matters": "..." } ],
  "key_takeaway": "1-2 sentences: what this document actually says/requires, stripped of all jargon"
}

Include EVERY jargon term, legalism, acronym, or technical phrase in the glossary. Do not skip any obligations, deadlines, dollar amounts, or conditions in the simplified text.

TEXT TO DECODE:
${i.text}`,
};

async function call(prompt, maxTokens) {
  const res = await fetch(`${BASE}/api/messages`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, max_tokens: maxTokens }), // non-streaming → full JSON
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error.message || 'API error');
  return data.content.filter((c) => c.type === 'text').map((c) => c.text).join('\n');
}
const parseJson = (s) => JSON.parse(s.replace(/```json\n?|\n?```/g, '').trim());
const words = (s) => (s.trim().match(/\S+/g) || []).length;
const sentences = (s) => (s.match(/[.!?。！？]+/g) || []).length;
const INFORMAL = /\b(u|thx|lmk|gonna|wanna|kinda)\b|n't|'ll|'re|'ve|'m\b/gi;
const FORMAL = /\b(pursuant|hereby|aforementioned|notwithstanding|heretofore|whereas|thereof)\b/gi;
const count = (s, re) => (s.match(re) || []).length;

const CHECKS = {
  enhance: (i, out) => {
    const r = {};
    r.non_empty = out.trim().length > 0;
    const ratio = words(out) / Math.max(1, words(i.text));
    r['length_ratio_0.5_to_3x'] = ratio >= 0.5 && ratio <= 3.5;
    r.preserves_must_keep = i.must_keep.every((k) => out.includes(k));
    r.no_meta_preamble = !/^\s*(here('|i)s|sure|certainly|below is|i've|i have)\b/i.test(out);
    if (i.tone_target === 'formal') r.tone_direction_signal = count(out, INFORMAL) <= count(i.text, INFORMAL);
    else if (i.tone_target === 'conversational') r.tone_direction_signal = count(out, FORMAL) <= count(i.text, FORMAL);
    else r.tone_direction_signal = true;
    return r;
  },
  translate: (i, out) => {
    const r = {}; let j;
    try { j = parseJson(out); r.valid_json = true; } catch { return { valid_json: false }; }
    r.translation_non_empty = !!(j.translation && j.translation.trim());
    r.detected_language_correct = (j.detected_language || '').toLowerCase().includes(i.expect_detected.toLowerCase());
    r.preserves_must_keep = i.must_keep.every((k) => (j.translation || '').includes(k));
    r.sentence_count_parity = Math.abs(sentences(j.translation || '') - i.sentences) <= 1;
    r.translation_differs_from_source = (j.translation || '').trim() !== i.text.trim();
    return r;
  },
  jargonary: (i, out) => {
    const r = {}; let j;
    try { j = parseJson(out); r.valid_json = true; } catch { return { valid_json: false }; }
    r.simplified_non_empty = !!(j.simplified_text && j.simplified_text.trim());
    r.key_takeaway_non_empty = !!(j.key_takeaway && j.key_takeaway.trim());
    const gloss = (j.jargon_glossary || []).map((g) => (g.term || '').toLowerCase()).join(' | ');
    const covered = i.expect_terms.filter((t) => gloss.includes(t.toLowerCase()));
    r.glossary_covers_terms = covered.length >= Math.ceil(i.expect_terms.length * 0.75);
    r._glossary_recall = `${covered.length}/${i.expect_terms.length}`;
    r.preserves_must_keep = i.must_keep.every((k) => (j.simplified_text || '').includes(k));
    return r;
  },
};

const MAXTOK = { enhance: 3000, translate: 3000, jargonary: 4000 };

(async () => {
  const tools = ONLY === 'all' ? ['enhance', 'translate', 'jargonary'] : [ONLY];
  for (const tool of tools) {
    const spec = JSON.parse(fs.readFileSync(path.join(__dirname, tool, 'inputs.json'), 'utf8'));
    console.log(`\n===== ${tool.toUpperCase()} (${spec.inputs.length} inputs) =====`);
    const agg = {}; let passAll = 0;
    for (const inp of spec.inputs) {
      let out;
      try { out = await call(buildPrompt[tool](inp), MAXTOK[tool]); }
      catch (e) { console.log(`  ${inp.id}: ERROR ${e.message}`); continue; }
      const r = CHECKS[tool](inp, out);
      const bools = Object.entries(r).filter(([k]) => !k.startsWith('_'));
      const passed = bools.filter(([, v]) => v).length;
      if (passed === bools.length) passAll++;
      for (const [k, v] of bools) { agg[k] = agg[k] || { pass: 0, n: 0 }; agg[k].n++; if (v) agg[k].pass++; }
      const extra = r._glossary_recall ? ` glossary=${r._glossary_recall}` : '';
      console.log(`  ${inp.id}: ${passed}/${bools.length}${extra}${passed < bools.length ? '  FAIL:[' + bools.filter(([, v]) => !v).map(([k]) => k).join(',') + ']' : ''}`);
    }
    console.log(`  -- per-check pass rate --`);
    for (const [k, { pass, n }] of Object.entries(agg)) console.log(`     ${k}: ${pass}/${n}`);
    console.log(`  clean inputs (all checks pass): ${passAll}/${spec.inputs.length}`);
  }
})();
