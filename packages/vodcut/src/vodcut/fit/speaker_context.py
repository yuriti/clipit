"""Words aligned to speaker turns: blocks of words with the same attribution, and the activity timeline.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/speaker_context.py) as it is; the only change: the window's
end comes from the packet (`context_window_ms`), so a recording shorter than 70 s gets a window of its own length.
Without a speaker diarization (SMTV on a computer without a graphics card) there are no turns: every word is `unknown`
and the timeline is one gap, which the legend says is not proof of silence.
"""
import collections
import copy

def merge_context(source):
    x=copy.deepcopy(source);words=x.pop('words');turns=x['acoustic_evidence'].pop('fully_contained_speaker_turns_ms')
    # Sweep exact intervals, merging adjacent equal sets. The track is automatic diarization, not human truth.
    end=x['context_window_ms'][1];points=sorted({0,end}|{v for t in turns for v in t[:2]});track=[]
    for a,b in zip(points,points[1:]):
     active=sorted({s for ta,tb,s in turns if ta<b and tb>a})
     if track and track[-1]['speakers']==active:track[-1]['end_ms']=b
     else:track.append({'start_ms':a,'end_ms':b,'speakers':active})
    aligned=[]
    for wid,a,b,txt,confidence in words:
     coverage=collections.Counter();both=0;any_ms=0
     for t in track:
      ms=max(0,min(b,t['end_ms'])-max(a,t['start_ms']))
      if not ms:continue
      for sp in t['speakers']:coverage[sp]+=ms
      if t['speakers']:any_ms+=ms
      if len(t['speakers'])>1:both+=ms
     candidates=sorted(coverage)
     if both:state='overlap_ambiguous'
     elif len(candidates)>1:state='speaker_boundary_ambiguous'
     elif not candidates:state='unknown'
     elif any_ms/(b-a)<.8:state='partial_coverage_uncertain'
     else:state='single_speaker_candidate'
     aligned.append({'word_id':wid,'start_ms':a,'end_ms':b,'text':txt,'asr_confidence':confidence,'speaker_id':candidates[0] if state=='single_speaker_candidate' else None,'attribution_status':state,'candidate_speakers':candidates,'coverage_by_speaker_ms':dict(coverage),'uncovered_ms':b-a-any_ms,'simultaneous_speech_ms':both})
    blocks=[]
    for w in aligned:
     signature=(w['speaker_id'],w['attribution_status'],w['candidate_speakers'])
     prev=blocks[-1] if blocks else None
     if prev and (prev['speaker_id'],prev['attribution_status'],prev['candidate_speakers'])==signature and w['start_ms']-prev['end_ms']<=800 and w['word_id'].split('-word-')[0]==prev['words'][-1]['word_id'].split('-word-')[0]:
      prev['words'].append(w);prev['end_ms']=w['end_ms'];prev['text']+=' '+w['text']
     else:blocks.append({'block_id':f'B{len(blocks)+1:03d}','start_ms':w['start_ms'],'end_ms':w['end_ms'],'speaker_id':w['speaker_id'],'attribution_status':w['attribution_status'],'candidate_speakers':w['candidate_speakers'],'text':w['text'],'words':[w]})
    x['speaker_context']={'method':'Exact interval intersections with saved diarization. Single speaker candidate requires only one intersecting speaker and >=80% word coverage; this threshold is a declared conservative heuristic, not calibrated confidence. Any concurrent interval keeps attribution ambiguous. Multiple sequential speakers within a word are boundary ambiguity, not simultaneous speech.','limitations':'Automatic labels may be wrong; identity, addressee, emotion and interruption intent are unknown. ASR is a mixed stream; overlapping speakers have NOT been separated into independent transcripts. Each original word appears exactly once; candidate lists do not mean every candidate uttered the same word. No active speaker is a diarization gap, not proof of silence.','speaker_ids':sorted({t[2] for t in turns}),'speech_blocks':blocks,'activity_timeline':track}
    return x,words,turns
