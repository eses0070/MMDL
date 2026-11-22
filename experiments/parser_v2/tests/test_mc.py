from copy import deepcopy
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from mc_parser import decide, map_answer, tail_policy
from replay import ROOT, load, evaluate, read_rows, run


OPTS={'A':'increase','B':'decrease','C':'unchanged'}


def cached(answer,status='matched'):
    return json.dumps({'status':status,'answer':answer,'reason':'Do not use this reasoning to select the answer'})


def call(text,options=OPTS,question='What happens?',finish='stop',answer=None,status='matched'):
    return decide(question,options,text,finish,cached(answer,status) if answer else None,'stop')


class Mapping(unittest.TestCase):
    def test_letter_and_text_without_prefix(self):
        r=call('Earlier thoughts.\n**B. decrease**')
        self.assertEqual(r['prediction'],'B')
        self.assertEqual(r['route'],'letter_with_literal_content')

    def test_markdown_answer_header(self):
        r=call('Work.\n✅ **Final Answer: A. increase**')
        self.assertEqual(r['prediction'],'A')

    def test_label_outside_option_keys_is_content(self):
        r=call('The observed region is H.\nCorrect Answer: **H**',{'A':'J','B':'H','C':'L'})
        self.assertEqual(r['prediction'],'B')

    def test_label_key_overlap_stays_uncertain(self):
        r=call('Final Answer: A',{'A':'C','B':'A','C':'E'},answer='A')
        self.assertIsNone(r['prediction'])
        self.assertEqual(r['reason'],'option_key_vs_diagram_label_ambiguous')
        r=call('Final Answer: option A',{'A':'C','B':'A','C':'E'})
        self.assertEqual(r['prediction'],'A')

    def test_letter_content_conflict_not_repaired(self):
        r=call('Final Answer: A. decrease',answer='A')
        self.assertIsNone(r['prediction'])
        self.assertTrue(r['hard_conflict'])

    def test_mass_option_mapping(self):
        r=call('Final Answer: 2500 g',{'A':'25 kg','B':'0.25 kg','C':'2.5 kg'},'What is the mass?')
        self.assertEqual(r['prediction'],'C')
        self.assertEqual(r['route'],'numeric_options')

    def test_letter_with_scaled_numeric_content(self):
        r=call('Final Answer: B. 3600 g',{'A':'2.8 kg','B':'3.6 kg','C':'4.4 kg'},'What is the mass?')
        self.assertEqual(r['prediction'],'B')
        self.assertEqual(r['route'],'letter_with_numeric_content')

    def test_percent_magnitude_not_lost(self):
        opts={'A':'60%','B':'0.6%','C':'6%'}
        self.assertEqual(call('Final Answer: 0.6 of the total',opts,'What percentage?')['prediction'],'A')
        self.assertEqual(call('Final Answer: 0.6%',opts,'What percentage?')['prediction'],'B')

    def test_currency_and_fraction_options(self):
        self.assertEqual(call('Answer: 1/8',{'A':'0.8','B':'0.125','C':'1.25'},'What value?')['prediction'],'B')
        self.assertEqual(call('Answer: 50 USD',{'A':'$50','B':'$500','C':'$5'},'What is the price in US dollars?')['prediction'],'A')

    def test_no_nearest_option_or_invented_unit(self):
        r=call('Final Answer: 2.7',{'A':'2.6','B':'2.8','C':'2.9'})
        self.assertIsNone(r['prediction'])
        r=call('Final Answer: 2700g',{'A':'2.7','B':'27','C':'270'})
        self.assertIsNone(r['prediction'])

    def test_multiple_equivalent_numeric_options(self):
        r=call('Final Answer: 1000g',{'A':'1 kg','B':'1000g','C':'2 kg'},'What is the mass?')
        self.assertIsNone(r['prediction'])
        self.assertEqual(map_answer('1 kg','What is the mass?',{'A':'1 kg','B':'1000g','C':'2 kg'})['reason'],'multiple_quantity_matches')

    def test_numeric_unknown_other_option_does_not_force_match(self):
        r=call('Answer: 1/2',{'A':'0.5','B':'several','C':'2'})
        self.assertIsNone(r['prediction'])

    def test_exact_text_never_substring_or_negation(self):
        self.assertIsNone(call('Answer: not increase')['prediction'])
        self.assertIsNone(call('Answer: increase or decrease')['prediction'])

    def test_final_option_list_is_not_choice(self):
        self.assertIsNone(call('Available options:\nA. increase\nB. decrease')['prediction'])


class CachedJudge(unittest.TestCase):
    def test_note_footer_requires_saved_judge_and_anchor(self):
        text='Work.\nFinal Answer: **B. decrease**\n\n*(Note: The explanation is tentative.)*'
        self.assertIsNone(call(text)['prediction'])
        r=call(text,answer='B')
        self.assertEqual(r['prediction'],'B')
        self.assertEqual(r['route'],'cached_qwen_supported')
        self.assertEqual(text[slice(*r['evidence_span'])],r['evidence_quote'])

    def test_legacy_correctness_is_not_used(self):
        text='Final Answer: C. unchanged\n\n(Note: No further observation.)'
        for status in ('matched','correct','incorrect'):
            self.assertEqual(call(text,answer='C. unchanged',status=status)['prediction'],'C')

    def test_saved_answer_must_agree_with_anchor(self):
        text='Final Answer: A. increase\n\n(Note: The explanation is tentative.)'
        self.assertIsNone(call(text,answer='B')['prediction'])

    def test_final_declarative_sentence(self):
        text='The evidence does not establish a cause. Therefore, option B is the correct answer as it describes a decrease.'
        r=call(text,answer='B')
        self.assertEqual(r['prediction'],'B')
        self.assertEqual(r['evidence_quote'],'Therefore, option B is the correct answer as it describes a decrease.')

    def test_conditional_quoted_or_retracted_statement_rejected(self):
        texts=['If option B is the correct answer we must check.',
               'Someone said option B is the correct answer.',
               '"option B is the correct answer"',
               'Option B is the correct answer?','option B is the correct answer. Actually I choose A.']
        for text in texts:
            with self.subTest(text=text):self.assertIsNone(call(text,answer='B')['prediction'])

    def test_note_retraction_and_changed_choice_rejected(self):
        for note in ('Actually choose A.','I reconsider.','Not B.','Instead choose A.','The answer is A.'):
            text='Final Answer: B. decrease\n\n(Note: '+note+')'
            with self.subTest(note=note):self.assertIsNone(call(text,answer='B')['prediction'])

    def test_multiple_answer_commitments_are_ambiguous(self):
        text='Answer: A. increase\nFinal Answer: B. decrease\n(Note: More work needed.)'
        self.assertIsNone(call(text,answer='B')['prediction'])

    def test_mid_reasoning_claim_is_not_final(self):
        self.assertIsNone(call('I calculated 2.5 kg.\nMore work is required.',{'A':'2.5 kg','B':'1 kg'},answer='A')['prediction'])

    def test_no_gt_or_id_interface(self):
        parameters=inspect.signature(decide).parameters
        self.assertFalse({'gold','gt','question_id','old_correct'} & set(parameters))

    def test_incomplete_generation_always_guarded(self):
        for finish in ('length','repetition_abort','error'):
            r=call('Final Answer: A. increase',finish=finish,answer='A')
            self.assertIsNone(r['prediction']);self.assertEqual(r['route'],'generation_guard')

    def test_context_limit_guarded(self):
        self.assertEqual(decide('What?',OPTS,'Answer: A','stop',context_budget_limited=True)['route'],'generation_guard')

    def test_cached_judge_finish_and_schema(self):
        text='Final Answer: A. increase\n(Note: extra text.)'
        self.assertIsNone(decide('What?',OPTS,text,'stop',cached('A'),'length')['prediction'])
        self.assertIsNone(decide('What?',OPTS,text,'stop','not-json','stop')['prediction'])


class Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bundle=load()

    def test_selection_is_exact_remaining46(self):
        b=self.bundle
        self.assertEqual(len(b['targets']),46)
        self.assertEqual(len(b['originally']),81)
        for qid in b['targets']:
            self.assertEqual(b['pm'][qid]['annotation']['question_type'],'multiple-choice')
            self.assertIs(b['cm'][qid]['parse_success'],False)
            self.assertIsNone(b['om'][qid]['correct'])

    def test_full_replay_preserves_untargeted854(self):
        b=self.bundle;rows,audits,summary=evaluate(b)
        self.assertEqual(len(audits),46);self.assertEqual(len(rows),900)
        for row in rows:
            if row['question_id'] not in b['targets']:self.assertEqual(row,b['cm'][row['question_id']])
        self.assertEqual(summary['new_judge_calls'],0)
        self.assertEqual(summary['open_records_unchanged'],53)

    def test_unresolved_is_distinct_from_scoring_wrong(self):
        rows,audits,summary=evaluate(self.bundle)
        self.assertTrue(any(not a['parse_recovered'] for a in audits))
        for a in audits:
            if not a['parse_recovered']:
                self.assertIsNone(a['answer_correct'])
                self.assertIs(a['scoring_correct'],False)

    def test_changing_gold_does_not_change_extraction(self):
        b=deepcopy(self.bundle)
        _,before,_=evaluate(b)
        for qid in b['targets']:
            options=b['om'][qid]['task']['options'];old=b['cm'][qid]['gold']
            b['cm'][qid]['gold']=next(key for key in options if key!=old)
        _,after,_=evaluate(b)
        self.assertEqual([a['extraction'] for a in before],[a['extraction'] for a in after])

    def test_non_target_subset_limit_preserved(self):
        rows,audits,summary=evaluate(self.bundle,3)
        self.assertEqual(len(audits),3);self.assertFalse(summary['complete_target_audit'])
        selected={a['question_id'] for a in audits}
        for r in rows:
            if r['question_id'] not in selected:self.assertEqual(r,self.bundle['cm'][r['question_id']])
        with self.assertRaises(ValueError):evaluate(self.bundle,-1)

    def test_output_raw_preservation_and_overwrite_guard(self):
        (ROOT/'results').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'results',prefix='test_') as d:
            out=Path(d)/'run';run(ROOT,out,dry_run=True);self.assertFalse(out.exists())
            run(ROOT,out)
            rows,_,raw=read_rows(out/'judgments.jsonl')
            for r in rows:
                if r==self.bundle['cm'][r['question_id']]:
                    self.assertEqual(raw[r['question_id']],self.bundle['raw_current'][r['question_id']])
            with self.assertRaises(FileExistsError):run(ROOT,out)

    def test_output_cannot_overwrite_inputs(self):
        for path in ('inputs/invalid','../outside','results'):
            with self.assertRaises(ValueError):run(ROOT,path,dry_run=True)


if __name__=='__main__':unittest.main()
