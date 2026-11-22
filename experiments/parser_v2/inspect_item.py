"""Read a replay audit, with optional full saved response. Does not change files."""
import argparse
import json
from pathlib import Path
from replay import ROOT, read_rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result-dir',type=Path,default=Path('results/mc46_run1'))
    p.add_argument('--id')
    p.add_argument('--show-response',action='store_true')
    a=p.parse_args();path=a.result_dir if a.result_dir.is_absolute() else ROOT/a.result_dir
    audits,am,_=read_rows(path/'audit.jsonl')
    if not a.id:
        for r in audits:
            print(r['question_id'],r['extraction']['route'],'prediction=',r['prediction'],
                  'answer_correct=',r['answer_correct'],'finish=',r['generation_finish_reason'])
        return
    if a.id not in am:p.error('ID was not audited in this run')
    _,pm,_=read_rows(ROOT/'inputs/predictions.jsonl')
    row=pm[a.id]
    out={'audit':am[a.id],'question':row['annotation']['question'],
         'options':{k:row['annotation'][k] for k in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if row['annotation'].get(k) is not None}}
    if a.show_response:out['raw_saved_response']=row['result']['gen']
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
