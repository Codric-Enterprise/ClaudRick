#!/usr/bin/env node
// Live grading harness for the analyzer test corpus.
// Runs each document through a running ReVision server and scores the analyzer's
// output against ground-truth.json. Requires the server up with an API key:
//   ANTHROPIC_API_KEY=sk-ant-... revision &
//   node grade.js http://localhost:8000
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const BASE = process.argv[2] || 'http://localhost:8000';
const gt = JSON.parse(fs.readFileSync(path.join(__dirname, 'ground-truth.json'), 'utf8'));

// Exact analyzer prompt from src/revision/static/index.html
function analyzerPrompt(text) {
  return `Analyze this text for manipulative language and hidden or predatory terms. Return ONLY valid JSON (no markdown, no explanations).

Text to analyze:
${text}

Return this exact JSON structure:
{
  "overall_risk_score": <0-100>,
  "deceptive_language": { "severity": "critical|high|medium|low", "detections": [ { "type": "description", "phrase": "exact phrase", "explanation": "why this is deceptive", "severity": "critical|high|medium|low" } ] },
  "tone_manipulation": { "severity": "critical|high|medium|low", "detections": [ { "type": "fear_appeal|emotional_appeal|greed_appeal|false_authority|false_consensus", "phrase": "exact phrase", "explanation": "how it manipulates", "severity": "critical|high|medium|low" } ] },
  "scare_tactics": { "severity": "critical|high|medium|low", "detections": [ { "type": "negative_consequence|threat|worst_case_framing|social_harm", "phrase": "exact phrase", "explanation": "the scare tactic", "severity": "critical|high|medium|low" } ] },
  "artificial_urgency": { "severity": "critical|high|medium|low", "detections": [ { "type": "time_pressure|scarcity_claim|now_or_never|limited_quantity", "phrase": "exact phrase", "explanation": "the urgency tactic", "severity": "critical|high|medium|low" } ] },
  "hidden_terms_and_costs": { "severity": "critical|high|medium|low", "detections": [ { "type": "hidden_fee|auto_renewal|forced_continuity|cancellation_obstruction|buried_limitation", "phrase": "exact phrase", "explanation": "what cost or obligation is buried or hard to escape", "severity": "critical|high|medium|low" } ] },
  "synthesis": "1-2 sentence summary of the overall manipulation profile and recommendations"
}`;
}

const docText = (file) =>
  execFileSync('unzip', ['-p', path.join(__dirname, file), 'word/document.xml'], { encoding: 'utf8' })
    .replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();
const overlaps = (a, b) => { const na = norm(a), nb = norm(b); return na.includes(nb) || nb.includes(na); };

async function analyze(text) {
  const res = await fetch(`${BASE}/api/messages`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: analyzerPrompt(text), max_tokens: 2000 }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error.message || 'API error');
  const raw = data.content.filter((i) => i.type === 'text').map((i) => i.text).join('\n');
  return JSON.parse(raw.replace(/```json\n?|\n?```/g, '').trim());
}

(async () => {
  const perCat = {}; let hit = 0, miss = 0;
  let controlPass = 0, bandPass = 0;
  console.log(`Grading ${gt.documents.length} docs against ${BASE}\n`);
  for (const d of gt.documents) {
    let a;
    try { a = await analyze(docText(d.file)); }
    catch (e) { console.log(`${d.id}: ERROR ${e.message}`); continue; }
    const score = a.overall_risk_score;
    const inBand = score >= d.expected_score_band[0] && score <= d.expected_score_band[1];
    if (inBand) bandPass++;
    if (d.kind === 'control' && score <= d.expected_score_band[1]) controlPass++;
    // recall: each planted pattern found among that category's detections?
    let dh = 0;
    for (const p of d.planted) {
      const dets = (a[p.category] && a[p.category].detections) || [];
      const found = dets.some((det) => overlaps(det.phrase, p.phrase));
      perCat[p.category] = perCat[p.category] || { hit: 0, total: 0 };
      perCat[p.category].total++;
      if (found) { hit++; dh++; perCat[p.category].hit++; } else miss++;
    }
    console.log(`${d.id} [${d.kind}] score=${score} band=${d.expected_score_band.join('-')}${inBand ? ' ✓' : ' ✗'} recall=${dh}/${d.planted.length}`);
  }
  console.log('\n== Recall by category ==');
  for (const c of Object.keys(perCat)) {
    const { hit: h, total: t } = perCat[c];
    console.log(`  ${c}: ${h}/${t} (${Math.round((h / t) * 100)}%)`);
  }
  const planted = hit + miss;
  console.log(`\nOverall recall: ${hit}/${planted} (${Math.round((hit / planted) * 100)}%)`);
  console.log(`Score-band accuracy: ${bandPass}/${gt.documents.length}`);
  console.log(`Controls under threshold: ${controlPass}/${gt.documents.filter((d) => d.kind === 'control').length}`);
})();
