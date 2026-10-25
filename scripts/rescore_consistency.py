"""Reproduce the consistency experiment from saved responses. No model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analysis.evaluate import evaluate,read_gold

EVIDENCE=ROOT/'docs/evaluation/day5_consistency'
WIRE={'category','sentiment','summary','evidence','keywords','condition','mentions_change'}

def canonical_sha256(data):
    """Ignore checkout line endings, while preserving all other file bytes."""
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()

def score(gold,predictions):
    result=evaluate(gold,predictions);s=result['summary']
    ng,np,tp=s['gold_items'],s['predicted_items'],s['pair_correct']
    s.update(pair_precision=tp/np if np else None,pair_recall=tp/ng if ng else None,
             pair_f1=2*tp/(ng+np) if ng+np else None,review_pair_exact_rate=s['pair_exact']/len(gold))
    return result

def rescore():
    manifest=json.loads((EVIDENCE/'manifest.json').read_text(encoding='utf-8'))
    for path,expected in manifest['packaged_file_sha256'].items():
        assert canonical_sha256((ROOT/path).read_bytes())==expected,f'Artifact changed: {path}'
    gold1,_=read_gold(ROOT/'data/reference_gold64_v1.jsonl',64)
    gold2,_=read_gold(ROOT/'data/reference_gold64_v2.jsonl',64)
    gold45,_=read_gold(ROOT/'data/test_reviews.jsonl',45)
    challenge,_=read_gold(ROOT/'data/consistency_challenge24.jsonl',24)
    originals={}
    for filename in ('reviews_p01.jsonl','reviews_p02.jsonl'):
        for line in (ROOT/'data/reference'/filename).read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                r=json.loads(line);assert r['id'] not in originals;originals[r['id']]=r
    # Portal files are regenerated for deployment. Historical scores must use
    # the frozen experimental baseline instead of those mutable portal files.
    baseline=json.loads((EVIDENCE/'baseline64_frozen.json').read_text(encoding='utf-8'))
    assert len(baseline)==64 and len({p['id'] for p in baseline})==64
    assert {p['id'] for p in baseline}==set(originals)
    assert all(r['text']==originals[r['id']]['text'] for r in gold1+gold2)
    saved=json.loads((EVIDENCE/'saved_predictions.json').read_text(encoding='utf-8'))
    cases={'baseline64_v1':(gold1,baseline),'baseline64_v2':(gold2,baseline),
      'candidate64_v3':(gold2,saved['candidate64_v3']),'baseline45':(gold45,saved['baseline45']),
      'candidate45_v3':(gold45,saved['candidate45_v3']),
      'challenge_baseline':(challenge,saved['challenge_baseline']),'challenge_candidate':(challenge,saved['challenge_candidate'])}
    results={name:score(g,p) for name,(g,p) in cases.items()}
    # Timing/usage are not reconstructed from a compact classification snapshot.
    compare_fields=['tp','fp','fn','sentiment_correct','sentiment_total','pair_correct','gold_items','predicted_items',
      'evidence_exact','failed','pair_exact','review_count','category_f1','sentiment_accuracy','evidence_exact_rate','pair_f1']
    for name,result in results.items():
        for key in compare_fields:
            assert result['summary'][key]==manifest['expected_summaries'][name][key],(name,key)
    b,c=results['baseline64_v2']['summary'],results['candidate64_v3']['summary']
    ob,oc=results['baseline45']['summary'],results['candidate45_v3']['summary']
    tb,tc=results['challenge_baseline']['summary'],results['challenge_candidate']['summary']
    checks={'all_saved_scores_reproduced':True,'source_texts_preserved':True,'artifact_hashes_valid':True,
      'dev_pair_f1_gain':c['pair_f1']>=b['pair_f1']+0.02,'dev_category':c['category_f1']>=b['category_f1'],
      'dev_sentiment':c['sentiment_accuracy']>=b['sentiment_accuracy'],'dev_exact_reviews':c['pair_exact']>=b['pair_exact'],
      'dev_evidence_exact':c['evidence_exact_rate']==1,'regression45_category':oc['category_f1']>=ob['category_f1'],
      'regression45_sentiment':oc['sentiment_accuracy']>=ob['sentiment_accuracy'],
      'regression45_evidence':oc['evidence_exact_rate']>=ob['evidence_exact_rate'],
      'challenge_pair_f1':tc['pair_f1']>=tb['pair_f1'],'challenge_category':tc['category_f1']>=tb['category_f1'],
      'all_candidate_evidence_exact':all(results[n]['summary']['evidence_exact_rate']==1 for n in ('candidate64_v3','candidate45_v3','challenge_candidate')),
      'no_candidate_failures':all(results[n]['summary']['failed']==0 for n in ('candidate64_v3','candidate45_v3','challenge_candidate'))}
    return {'checks':checks,'new_api_calls':0,'label_status':manifest['label_status'],'results':results}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='consistency_eval.local.json')
    args=parser.parse_args();result=rescore()
    output=Path(args.output)
    if not output.is_absolute():output=ROOT/output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'checks':result['checks'],'new_api_calls':0,'output':str(output)},ensure_ascii=False,indent=2))
    return int(not all(result['checks'].values()))

if __name__=='__main__':raise SystemExit(main())
