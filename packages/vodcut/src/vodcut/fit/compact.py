"""The lossless compact form of a Fit packet: words as rows, per-word speaker coverage only where it differs from the block.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/compact.py) unchanged; `expand(compact(x)) == x` is checked
for every packet. LEGEND goes into the prompt after the policy.
"""
import copy

LEGEND = '''
Compact input format (the assessment criteria above still apply):
speaker_context.speech_blocks preserves the same chronological blocks. Each block's speaker_id, attribution_status and candidate_speakers apply to EVERY word in that block; these remain automatic hypotheses, not established identities.
Each words row is [word_id,start_ms,end_ms,text,asr_confidence]. Positions are fixed. IDs and milliseconds are original; use them unchanged in the response. The block text is the text of all its words joined by spaces, and is not duplicated separately.
Word defaults: if the block's speaker_id is not null, coverage_by_speaker_ms={speaker_id: end_ms-start_ms}, uncovered_ms=0, simultaneous_speech_ms=0; if speaker_id=null, coverage_by_speaker_ms={}, uncovered_ms=end_ms-start_ms, simultaneous_speech_ms=0. word_coverage_exceptions contains [word_id,coverage_by_speaker_ms,uncovered_ms,simultaneous_speech_ms] rows replacing all three values for that word. Exceptions preserve every partial coverage and overlap. Status/candidates always come from the block, including for exceptions. Do not interpret null as one known speaker.
activity_timeline rows are [start_ms,end_ms,speakers], where speakers lists simultaneously detected voices. An empty list is a diarization gap, not proven silence. Other fields and acoustic data retain their existing format. Return the JSON response schema, not tables.
'''

def compact(x):
    x = copy.deepcopy(x)
    sc = x['speaker_context']
    for b in sc['speech_blocks']:
        assert b['text'] == ' '.join(w['text'] for w in b['words'])
        del b['text']
        rows, exceptions = [], []
        for w in b['words']:
            assert all(w[k] == b[k] for k in ['speaker_id','attribution_status','candidate_speakers'])
            rows.append([w[k] for k in ['word_id','start_ms','end_ms','text','asr_confidence']])
            duration = w['end_ms'] - w['start_ms']
            default = [{b['speaker_id']:duration},0,0] if b['speaker_id'] is not None else [{},duration,0]
            actual = [w[k] for k in ['coverage_by_speaker_ms','uncovered_ms','simultaneous_speech_ms']]
            if actual != default: exceptions.append([w['word_id'], *actual])
        b['words'] = rows
        b['word_coverage_exceptions'] = exceptions
    sc['activity_timeline'] = [[t['start_ms'],t['end_ms'],t['speakers']] for t in sc['activity_timeline']]
    return x

def expand(x):
    x = copy.deepcopy(x)
    sc = x['speaker_context']
    for b in sc['speech_blocks']:
        exceptions = {r[0]: r[1:] for r in b.pop('word_coverage_exceptions')}
        words = []
        for row in b['words']:
            w = dict(zip(['word_id','start_ms','end_ms','text','asr_confidence'],row))
            w.update({k:b[k] for k in ['speaker_id','attribution_status','candidate_speakers']})
            duration = w['end_ms'] - w['start_ms']
            default = [{b['speaker_id']:duration},0,0] if b['speaker_id'] is not None else [{},duration,0]
            values = exceptions.pop(w['word_id'], default)
            w.update(dict(zip(['coverage_by_speaker_ms','uncovered_ms','simultaneous_speech_ms'],values)))
            words.append(w)
        assert not exceptions
        b['words'] = words
        b['text'] = ' '.join(w['text'] for w in words)
    sc['activity_timeline'] = [dict(zip(['start_ms','end_ms','speakers'],t)) for t in sc['activity_timeline']]
    return x

