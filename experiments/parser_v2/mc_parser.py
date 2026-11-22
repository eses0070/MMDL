"""GT/ID-blind MC answer extraction + frozen AE quantities + cached judge support.

The judge proposes an option, never its correctness. Deterministic evidence checks
must independently support that proposal. This does not validate reasoning.
"""
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent/'frozen'))
from numeric_rules import compare_quantities, VERSION as NUMERIC_VERSION
from terminal_format import format_only

VERSION = 'mc46-hybrid-v1'
PREFIX = re.compile(r'^(?:(?:so|therefore|thus)[, ]+)?(?:(?:the|my)\s+)?(?:final\s+|correct\s+|best\s+)?answer(?:\s+is)?\s*[:=]\s*', re.I)
NATURAL = re.compile(r'\boption\s+([A-Z])\s+is\s+the\s+(?:correct|best|final)\s+answer\b')


def clean(text):
    text=re.sub(r'^[\s#>✅✔➡️→]+','',text)
    return format_only(text)


def same_text(a,b):
    # No substring, stem, synonym, case-fold, unit stripping or numeric tolerance.
    a,b=clean(a),clean(b)
    return a==b or a==b+'.'


def unknown(reason, **details):
    return {'status':'uncertain','prediction':None,'reason':reason,**details}


def matched(key, route, **details):
    return {'status':'matched','prediction':key,'route':route,**details}


def check_options(options):
    if not isinstance(options,dict) or len(options)<2 or any(
        not re.fullmatch('[A-Z]',k) or not isinstance(v,str) or not v.strip() for k,v in options.items()):
        raise ValueError('Invalid options')


def map_content(answer, question, options):
    """Map one whole answer against ALL option contents; never against GT."""
    checks={k:compare_quantities(question,format_only(v),answer) for k,v in options.items()}
    numeric_matches=[k for k,v in checks.items() if v['decision'] is True]
    if len(numeric_matches)>1:
        return unknown('multiple_quantity_matches',numeric_checks=checks)
    if len(numeric_matches)==1 and all(v['decision'] is not None for v in checks.values()):
        return matched(numeric_matches[0],'numeric_options',numeric_checks=checks)
    exact=[k for k,v in options.items() if same_text(answer,v)]
    if len(exact)>1:
        return unknown('multiple_literal_matches',numeric_checks=checks)
    if len(exact)==1:
        return matched(exact[0],'literal_option_content',numeric_checks=checks)
    if numeric_matches:
        return unknown('other_options_not_numerically_evaluable',numeric_checks=checks)
    if all(v['decision'] is False for v in checks.values()):
        return unknown('no_quantity_option_matches',numeric_checks=checks)
    return unknown('unsupported_or_unmatched_content',numeric_checks=checks)


def map_answer(answer, question, options):
    check_options(options)
    answer=clean(answer)
    if not answer or len(answer)>2048:return unknown('answer_empty_or_too_long')
    explicit=re.fullmatch(r'(?:option|choice)\s+\(?([A-Z])\)?[.!]?',answer,re.I)
    if explicit:
        k=explicit[1].upper()
        return matched(k,'explicit_option_key') if k in options else unknown('invalid_option_key')
    labelled=re.fullmatch(r'(?:option\s+)?(?:\(([A-Z])\)|([A-Z])[.):])\s*(.+)',answer)
    if labelled:
        k=labelled[1] or labelled[2];content=clean(labelled[3])
        if k not in options:return unknown('invalid_option_key')
        numeric=compare_quantities(question,format_only(options[k]),content)
        if same_text(content,options[k]):
            return matched(k,'letter_with_literal_content',content=content,numeric_check=numeric)
        if numeric['decision'] is True:
            return matched(k,'letter_with_numeric_content',content=content,numeric_check=numeric)
        return unknown('letter_content_conflict_or_unsupported',hard_conflict=True,numeric_check=numeric)
    bare=re.fullmatch(r'\(?([A-Z])\)?[.!]?',answer)
    if bare:
        k=bare[1]
        content_keys=[key for key,v in options.items() if same_text(k,v)]
        if k in options:
            if any(key!=k for key in content_keys):
                return unknown('option_key_vs_diagram_label_ambiguous',hard_conflict=True)
            return matched(k,'bare_option_key')
        if len(content_keys)==1:
            return matched(content_keys[0],'diagram_label_as_option_content')
        return unknown('invalid_or_ambiguous_label')
    return map_content(answer,question,options)


def lines_with_spans(response):
    result=[];offset=0
    for line in response.splitlines(keepends=True):
        start=offset;offset+=len(line)
        content=line.rstrip('\r\n')
        if content.strip():
            result.append({'text':content,'span':[start,start+len(content)]})
    while result and re.fullmatch(r'\s*[-_*]{3,}\s*',result[-1]['text']):result.pop()
    return result


def final_line(response,question,options):
    lines=lines_with_spans(response)
    if not lines:return unknown('empty_response')
    last=lines[-1];line=clean(last['text']);marker=PREFIX.match(line)
    payload=clean(line[marker.end():]) if marker else line
    # Do not treat the last row of an option list as a selected answer.
    if not marker and len(lines)>1 and all(re.match(r'^[A-Z][.)]\s',clean(l['text'])) for l in lines[-2:]):
        return unknown('terminal_option_listing')
    result=map_answer(payload,question,options)
    return {**result,'answer_text':payload,'evidence_quote':last['text'],'evidence_span':last['span'],
            'candidate_method':'last_nonempty_answer_line'}


def tail_policy(tail,key,options):
    """Allow only an explicit Note footer without a new choice/retraction.

The note can criticize factual reasoning; factual correctness is not evaluated.
Arbitrary trailing reasoning or a changed/withdrawn choice remains unresolved.
"""
    if not tail.strip():return True,'nothing_after_answer'
    t=tail.strip()
    if len(t)>1800 or not re.match(r'^[*_\s(]*Note\s*:',t,re.I):
        return False,'trailing_text_is_not_note_footer'
    if re.search(r'\b(?:reconsider|instead|withdraw|retract|ignore (?:my |the )?(?:answer|choice)|change (?:my |the )?(?:answer|choice))\b',t,re.I):
        return False,'trailing_reconsideration'
    patterns=[r'\b(?:option|choice)\s+([A-Z])\b',r'\banswer\s*(?:is|:|=)\s*\**\(?([A-Z])\b',
              r'(?<!\w)([A-Z])[.)]\s',r'\b(?:choose|select|pick)\s+(?:option\s+)?\**([A-Z])\b']
    later=[m[1].upper() for pattern in patterns for m in re.finditer(pattern,t)]
    if any(k in options and k!=key for k in later):return False,'trailing_different_choice'
    if re.search(r'\b(?:not|never)\s+(?:(?:option|choice)\s+)?'+re.escape(key)+r'\b',t,re.I):
        return False,'trailing_choice_negation'
    return True,'note_footer_without_new_choice'


def cached_proposal(raw,finish_reason,question,options):
    if finish_reason!='stop' or not isinstance(raw,str):return unknown('cached_judge_incomplete')
    try:value=json.loads(raw)
    except (ValueError,TypeError):return unknown('cached_judge_invalid_json')
    if not isinstance(value,dict) or set(value)!={'status','answer','reason'} or not isinstance(value['reason'],str):
        return unknown('cached_judge_invalid_schema')
    if value['status'] not in ('matched','correct','incorrect') or not isinstance(value['answer'],str):
        return unknown('cached_judge_no_answer')
    proposal=map_answer(value['answer'],question,options)
    return {**proposal,'raw_answer_field':value['answer'],'raw_status_ignored':value['status'],
            'policy':'answer field only; do not use cached correctness or reasoning'}


def supported_cached_fallback(response,question,options,proposal):
    """A cached LLM answer alone is not enough: find a committed literal anchor."""
    if proposal['status']!='matched':return unknown('cached_proposal_not_mappable',proposal=proposal)
    key=proposal['prediction'];lines=lines_with_spans(response);anchors=[]
    for i,line in enumerate(lines):
        text=clean(line['text']);marker=PREFIX.match(text)
        if marker:
            payload=clean(text[marker.end():]);start,end=line['span']
            if not payload and i+1<len(lines):
                payload=clean(lines[i+1]['text']);end=lines[i+1]['span'][1]
            mapped=map_answer(payload,question,options)
            anchors.append({'mapping':mapped,'answer_text':payload,'span':[start,end],'kind':'explicit_answer_marker'})
        else:
            # A declarative option choice near the end, not a question, hypothetical or quotation.
            natural=list(NATURAL.finditer(line['text']))
            if natural and i==len(lines)-1 and len(natural)==1:
                m=natural[0];raw=line['text']
                boundaries=list(re.finditer(r'[.!?]\s+',raw[:m.start()]))
                clause_start=boundaries[-1].end() if boundaries else 0
                prefix=raw[clause_start:m.start()]
                suffix=raw[m.end():]
                unsafe=(re.search(r'\b(?:if|suppose|assuming|whether|not|never|maybe|perhaps|said|quote|example)\b',prefix,re.I)
                    or '?' in raw[clause_start:] or re.search(r'[.!?]\s+\S',suffix)
                    or any(c in raw[clause_start:m.end()] for c in ('"','“','”')))
                k=m[1]
                if not unsafe and k in options:
                    anchors.append({'mapping':matched(k,'declarative_option_choice'),
                        'answer_text':'option '+k,'span':[line['span'][0]+clause_start,line['span'][1]],
                        'kind':'last_sentence_declarative_choice'})
    usable=[a for a in anchors if a['mapping']['status']=='matched']
    # Contradictory or unsupported explicit commitments are not resolved by choosing the GT.
    if len(usable)!=1 or len(anchors)!=1:
        return unknown('no_unique_supported_commitment',proposal=proposal,anchor_count=len(anchors))
    anchor=usable[0]
    if anchor['mapping']['prediction']!=key:
        return unknown('cached_proposal_conflicts_with_commitment',proposal=proposal,anchor=anchor)
    allowed,reason=tail_policy(response[anchor['span'][1]:],key,options)
    if not allowed:return unknown(reason,proposal=proposal,anchor=anchor)
    start,end=anchor['span']
    return matched(key,'cached_qwen_supported',answer_text=anchor['answer_text'],
        evidence_quote=response[start:end],evidence_span=[start,end],
        proposal=proposal,anchor=anchor,tail_policy=reason)


def decide(question,options,response,finish_reason,cached_raw=None,cached_finish=None,context_budget_limited=False):
    """No gold, IDs, old correctness, images, or repaired predictions are accepted."""
    check_options(options)
    if not isinstance(response,str):raise ValueError('Missing response')
    if finish_reason!='stop' or context_budget_limited:
        return unknown('incomplete_generation',route='generation_guard',generation_finish_reason=finish_reason)
    direct=final_line(response,question,options)
    if direct['status']=='matched':return {**direct,'stage':'rules','cached_judge_used':False}
    if direct.get('hard_conflict'):
        return {**direct,'route':'unresolved_conflict','cached_judge_used':False}
    proposal=cached_proposal(cached_raw,cached_finish,question,options)
    fallback=supported_cached_fallback(response,question,options,proposal)
    if fallback['status']=='matched':
        return {**fallback,'stage':'cached_llm_fallback','cached_judge_used':True,'direct_attempt':direct}
    return {**fallback,'route':'unresolved_fallback','stage':'cached_llm_fallback',
            'cached_judge_used':True,'direct_attempt':direct}
